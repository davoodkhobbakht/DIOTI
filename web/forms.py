# ============================================
# forms.py (فرم نظرات و فرم‌های دیگر)
# ============================================
# apps/core/forms.py

from django import forms
from django.core.validators import RegexValidator, EmailValidator
from django.utils import timezone
from .models import Comment, Post
import re


class CommentForm(forms.ModelForm):
    """فرم ثبت نظر با اعتبارسنجی پیشرفته"""
    
    # فیلدهای اضافی برای اعتبارسنجی بیشتر
    author_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'نام و نام خانوادگی',
            'id': 'comment-name',
        }),
        validators=[
            RegexValidator(
                regex=r'^[\u0600-\u06FF\s]+$',
                message='لطفا نام خود را به فارسی وارد کنید',
                code='invalid_name'
            )
        ],
        error_messages={
            'required': 'لطفا نام خود را وارد کنید',
            'max_length': 'نام نمی‌تواند بیشتر از ۱۰۰ کاراکتر باشد',
        }
    )
    
    author_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@email.com',
            'id': 'comment-email',
        }),
        validators=[
            EmailValidator(message='لطفا یک ایمیل معتبر وارد کنید'),
        ],
        error_messages={
            'required': 'لطفا ایمیل خود را وارد کنید',
            'invalid': 'لطفا یک ایمیل معتبر وارد کنید',
        }
    )
    
    author_website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://yourwebsite.com (اختیاری)',
            'id': 'comment-website',
        }),
        error_messages={
            'invalid': 'لطفا یک آدرس وبسایت معتبر وارد کنید',
        }
    )
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'متن نظر شما...',
            'id': 'comment-content',
            'rows': 5,
            'cols': 50,
        }),
        validators=[
            RegexValidator(
                regex=r'^.{5,500}$',
                message='نظر باید بین ۵ تا ۵۰۰ کاراکتر باشد',
                code='invalid_length'
            )
        ],
        error_messages={
            'required': 'لطفا متن نظر را وارد کنید',
        }
    )
    
    # فیلد مخفی برای جلوگیری از اسپم (Honeypot)
    website_trap = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'style': 'display: none;',
            'tabindex': '-1',
            'autocomplete': 'off',
        })
    )
    
    class Meta:
        model = Comment
        fields = ['author_name', 'author_email', 'author_website', 'content']
    
    def __init__(self, *args, **kwargs):
        self.post = kwargs.pop('post', None)
        super().__init__(*args, **kwargs)
        
        # اضافه کردن کلاس‌های CSS به فیلدها
        for field_name, field in self.fields.items():
            if 'class' in field.widget.attrs:
                field.widget.attrs['class'] += ' form-control'
            else:
                field.widget.attrs['class'] = 'form-control'
    
    def clean_author_name(self):
        """پاکسازی و اعتبارسنجی نام کاربر"""
        name = self.cleaned_data.get('author_name', '').strip()
        
        # حذف فاصله‌های اضافی
        name = re.sub(r'\s+', ' ', name)
        
        # جلوگیری از نام‌های تکراری یا بی‌معنی
        forbidden_names = ['admin', 'مدیر', 'ادمین', 'user', 'test', 'کاربر']
        if name.lower() in forbidden_names:
            raise forms.ValidationError('این نام مجاز نیست. لطفا نام واقعی خود را وارد کنید.')
        
        # جلوگیری از نام‌های خیلی کوتاه
        if len(name) < 3:
            raise forms.ValidationError('نام باید حداقل ۳ کاراکتر باشد.')
        
        return name
    
    def clean_author_email(self):
        """اعتبارسنجی ایمیل و جلوگیری از ایمیل‌های موقت"""
        email = self.cleaned_data.get('author_email', '').strip().lower()
        
        # جلوگیری از ایمیل‌های موقت
        temp_email_domains = [
            'tempmail.com', '10minutemail.com', 'guerrillamail.com',
            'mailinator.com', 'yopmail.com', 'throwawaymail.com'
        ]
        
        for domain in temp_email_domains:
            if domain in email:
                raise forms.ValidationError('ایمیل موقت قابل قبول نیست. لطفا از ایمیل واقعی خود استفاده کنید.')
        
        return email
    
    def clean_website_trap(self):
        """Honeypot: اگر این فیلد پر شده بود، یعنی ربات است"""
        website_trap = self.cleaned_data.get('website_trap', '')
        if website_trap:
            raise forms.ValidationError('اسپم تشخیص داده شد.')
        return website_trap
    
    def clean_content(self):
        """پاکسازی و اعتبارسنجی محتوای نظر"""
        content = self.cleaned_data.get('content', '').strip()
        
        # جلوگیری از لینک‌های زیاد
        link_count = len(re.findall(r'https?://', content))
        if link_count > 2:
            raise forms.ValidationError('لطفا از درج لینک‌های زیاد خودداری کنید.')
        
        # جلوگیری از کلمات زشت (می‌توانی لیست را تکمیل کنی)
        bad_words = ['کلمه‌ی رکیک1', 'کلمه‌ی رکیک2']  # لیست کلمات نامناسب را خودت تکمیل کن
        for word in bad_words:
            if word in content.lower():
                raise forms.ValidationError('نظر شما شامل کلمات نامناسب است. لطفا اصلاح کنید.')
        
        # محدودیت کاراکتر
        if len(content) < 5:
            raise forms.ValidationError('نظر شما بسیار کوتاه است.')
        
        if len(content) > 1000:
            raise forms.ValidationError('نظر شما بسیار طولانی است (حداکثر ۱۰۰۰ کاراکتر).')
        
        return content
    
    def save(self, commit=True):
        """ذخیره نظر با اطلاعات اضافی"""
        comment = super().save(commit=False)
        
        # تنظیم پست مرتبط
        if self.post:
            comment.post = self.post
        
        # نظرات جدید پیش‌فرض تایید نشده هستند (مگر کاربر خاص)
        comment.is_approved = False
        
        # ذخیره IP کاربر (اگر در مدل داشته باشی)
        # comment.user_ip = self.request.META.get('REMOTE_ADDR')
        
        if commit:
            comment.save()
            self.save_m2m()
        
        return comment


class SearchForm(forms.Form):
    """فرم جستجوی پیشرفته"""
    query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'search-input',
            'placeholder': 'جستجو در مطالب...',
            'autocomplete': 'off',
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'search-select'}),
        label='دسته‌بندی'
    )
    
    post_type = forms.ChoiceField(
        choices=[('', 'همه')] + list(Post.TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'search-select'}),
        label='نوع مطلب'
    )
    
    order_by = forms.ChoiceField(
        choices=[
            ('-published_at', 'جدیدترین'),
            ('views_count', 'پربازدیدترین'),
            ('seo_score', 'بهترین سئو'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'search-select'}),
        label='مرتب‌سازی'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Category
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
    
    def clean_query(self):
        query = self.cleaned_data.get('query', '').strip()
        # حذف کاراکترهای خاص
        query = re.sub(r'[^\w\s\u0600-\u06FF]', '', query)
        return query


class ContactForm(forms.Form):
    """فرم تماس با ما"""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'نام شما',
        }),
        error_messages={'required': 'لطفا نام خود را وارد کنید'}
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ایمیل شما',
        }),
        error_messages={'required': 'لطفا ایمیل خود را وارد کنید'}
    )
    
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'موضوع پیام',
        }),
        error_messages={'required': 'لطفا موضوع را وارد کنید'}
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'متن پیام شما...',
            'rows': 6,
        }),
        error_messages={'required': 'لطفا متن پیام را وارد کنید'}
    )
    
    # Honeypot برای جلوگیری از اسپم
    honeypot = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'style': 'display:none;'})
    )
    
    def clean_honeypot(self):
        if self.cleaned_data.get('honeypot'):
            raise forms.ValidationError('اسپم تشخیص داده شد.')
        return self.cleaned_data.get('honeypot')


class NewsletterForm(forms.Form):
    """فرم عضویت در خبرنامه"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'newsletter-input',
            'placeholder': 'ایمیل خود را وارد کنید',
        }),
        error_messages={
            'required': 'لطفا ایمیل خود را وارد کنید',
            'invalid': 'ایمیل معتبر نیست'
        }
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        
        # جلوگیری از ایمیل‌های تکراری (می‌توانی با دیتابیس چک کنی)
        # if Subscriber.objects.filter(email=email).exists():
        #     raise forms.ValidationError('این ایمیل قبلاً ثبت نام کرده است.')
        
        return email


class AdminCommentFilterForm(forms.Form):
    """فرم فیلتر نظرات در پنل مدیریت"""
    status = forms.ChoiceField(
        choices=[('all', 'همه'), ('approved', 'تایید شده'), ('pending', 'در انتظار تایید')],
        required=False,
        widget=forms.Select(attrs={'class': 'filter-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'filter-date'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'filter-date'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'جستجو در نظرات...', 'class': 'filter-search'})
    )


