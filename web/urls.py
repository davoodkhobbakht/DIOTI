
# ============================================
# 4. URLS.PY (مسیرهای سایت)
# ============================================
# seo_site/urls.py

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from .views import (
    HomeView, PostDetailView, CategoryView, TagView, 
    SearchView, about_page, contact_page, robots_txt
)
from .views import PostSitemap, CategorySitemap

sitemaps = {
    'posts': PostSitemap,
    'categories': CategorySitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    
    # صفحات اصلی
    path('', HomeView.as_view(), name='home'),
    path('about/', about_page, name='about'),
    path('contact/', contact_page, name='contact'),
    path('search/', SearchView.as_view(), name='search'),
    
    # پست‌ها
    path('post/<slug:slug>/', PostDetailView.as_view(), name='post_detail'),
    # دسته‌بندی - استفاده از re_path برای پشتیبانی از فارسی
    re_path(r'^category/(?P<slug>[\w\-]+)/$', CategoryView.as_view(), name='category_detail'),
    # دسته‌بندی - تغییر الگو برای پشتیبانی از فارسی
    path('category/<slug:slug>/', CategoryView.as_view(), name='category_detail'),
    
    # برچسب‌ها - تغییر الگو برای پشتیبانی از فارسی
    path('tag/<slug:slug>/', TagView.as_view(), name='tag_detail'),
    
    # سئو و نقشه سایت
    path('robots.txt', robots_txt, name='robots'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    