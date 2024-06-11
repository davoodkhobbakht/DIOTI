import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from celery import shared_task
from django.http import JsonResponse
from .models import Product
import requests
from bs4 import BeautifulSoup
from django.utils import timezone
import datetime
import logging


logger = logging.getLogger('myapp')
logger.setLevel(logging.INFO)



def translate_persian_numerals_to_latin(text):
    persian_numerals = '۰۱۲۳۴۵۶۷۸۹'
    latin_numerals = '0123456789'
    translation_table = str.maketrans(persian_numerals, latin_numerals)
    return text.translate(translation_table)


def scrape_price(url):
    try:
        #logger.info(f'getting url {url}')
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            price = None
            if "https://www.afrangdigital.com/" in url:
                price_element = soup.find('span', itemprop='price')
                if price_element:
                    price = price_element.get_text(strip=True)
                    if price != 'تماس بگیرید':
                        price = price.replace('ریال', '').replace(',', '').strip()[:-1]
                    else:
                        price = 'CallUs'
            elif "https://noornegar.com/" in url or "https://www.didnegar.com/" in url:
                product_box = soup.find('div', class_='products-inner') if "https://noornegar.com/" in url else soup.find('div', class_='woocommerce-main-3-row-single')
                price_element = product_box.find('span', class_='woocommerce-Price-amount') if product_box else None
                if price_element:
                    price = price_element.find('bdi').get_text(strip=True)
                    if price:
                        price = translate_persian_numerals_to_latin(price.replace('تومان', '').replace(',', '').strip())
                else:
                    price = 'CallUs'
            return price
    except Exception as e:
        return f'error {e}'


@shared_task
def scrape_update_product_prices():
    products = Product.objects.filter(target_link__isnull=False)
    logger.info(products.count())
    logger.info('###########Scrap Start###########')
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(scrape_price, product.target_link): product for product in products }
        for future in as_completed(futures):
            product = futures[future]
            #print(product.last_scrape < timezone.now() - datetime.timedelta(hours=1) )
            try:
                price = future.result()
                if price and 'error' not in price:
                    if price != 'CallUs':
                        product.scrap_price = price
                        product.crawl_status = "Success"
                    else:
                        product.scrap_price = 'CallUs'
                        product.crawl_status = "Call Us Price"  
                    product.last_scrape = timezone.now()
                    product.save()
                    logger.info(f'Updated Database price for {product.name} to {price}')
                else:
                    product.scrap_price = ""
                    product.crawl_status = price
                    product.last_scrape = timezone.now()
                    product.save()
                    logger.info(f'Failed to update price for {product.name}')
            except Exception as e:
                logger.error(f"An error occurred: {e}")


    logger.info('###########Scrap Ended###########')







@shared_task
def web_update_all_prices_task():
    products = Product.objects.filter(
        target_link__isnull=False,
        crawl_status__in=['Success', 'Call Us Price']
    ).exclude(target_link__in =['None',None])
    logger.info('###########WebUpdate Start###########')
    logger.info(len(products))
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(update_website_price, product,): product for product in products 
                   }
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                product = futures[future]
                logger.error(f"An error occurred with product {product.id}: {e}")

    logger.info('###########WebUpdate End###########')
    logger.handlers[0].flush()  # 
    return True


def woocomerce_login():

    api_key = 'ck_a862f3205a9991d1bed42d48104616f92fa702e7'  # Replace with your actual API key
    api_secret = 'cs_fe83d949d4d90a1f2fba42b903ab87b256543f06'  # Replace with your actual API secret
    auth_string = f'{api_key}:{api_secret}'
    auth_header = 'Basic ' + base64.b64encode(auth_string.encode()).decode()
    headers = {
        'Authorization': auth_header ,
        'Content-Type': 'application/json'
        }

    return headers


def update_website_price(product,):
    if not product.target_link:
        logger.info(f'No target_link for product id: {product.id}: {product.name}')
        return

    product_id = product.id
    new_price = product.scrap_price
    status = product.crawl_status
    link = product.target_link
    product_name = product.name
    base_url = 'https://doorbinshot.com/wp-json/wc/v3'
    endpoint = '/products'
    update_url = f'{base_url}{endpoint}/{product_id}'
    headers = woocomerce_login()
    if new_price:
        new_price_data = {
            'regular_price': '' if new_price == 'CallUs' or new_price == None else new_price
        }
 
    response = requests.put(update_url, headers=headers, data=json.dumps(new_price_data))
    if response.status_code == 200:
        product.last_web_price_update = timezone.now()
        product.save(update_fields=['last_web_price_update'])
        logger.info(f'Web Price updated Product ID {product_id} : {product_name} : {new_price}')
    else:
        logger.info(response.content.decode('utf-8'))
        logger.info(f'Error updating price for Product ID {product_id} : {response.status_code}')
    return
