#web/models.py

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from ckeditor.fields import RichTextField  # pip install django-ckeditor
import json

class Category(models.Model):
    """دسته‌بندی مطالب"""
    name = models.CharField(max_length=100, verbose_name="نام دسته‌بندی")
    slug = models.SlugField(unique=True, allow_unicode=True, verbose_name="اسلاگ")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    woo_id = models.IntegerField(null=True, blank=True, verbose_name="ID در ووکامرس")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('category_detail', args=[self.slug])


class Tag(models.Model):
    """برچسب‌ها برای سئو بهتر"""
    name = models.CharField(max_length=50, unique=True, verbose_name="برچسب")
    slug = models.SlugField(unique=True, allow_unicode=True)
    
    class Meta:
        verbose_name = "برچسب"
        verbose_name_plural = "برچسب‌ها"
    
    def __str__(self):
        return self.name


class Post(models.Model):
    """پست وبلاگ با تمام داده‌های سئو"""
    
    STATUS_CHOICES = (
        ('draft', '📝 پیش‌نویس'),
        ('published', '✅ منتشر شده'),
        ('scheduled', '⏰ زمانبندی شده'),
        ('trash', '🗑 زباله دان'),
    )
    
    TYPE_CHOICES = (
        ('informative', '📚 آموزشی'),
        ('marketing', '📢 بازاریابی'),
        ('news', '📰 خبری'),
        ('review', '⭐ نقد و بررسی'),
    )
    
    # فیلدهای اصلی
    title = models.CharField(max_length=500, verbose_name="عنوان")
    slug = models.SlugField(unique=True, allow_unicode=True, max_length=500, verbose_name="اسلاگ")
    content = RichTextField(verbose_name="محتوا")
    excerpt = models.TextField(blank=True, max_length=300, verbose_name="خلاصه")
    
    # دسته‌بندی و برچسب‌ها
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='posts', verbose_name="دسته‌بندی")
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts', verbose_name="برچسب‌ها")
    
    # نوع و وضعیت
    post_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='informative', verbose_name="نوع پست")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="وضعیت")
    
    # داده‌های سئو (کلیدی)
    focus_keyword = models.CharField(max_length=100, blank=True, verbose_name="کلمه کلیدی اصلی")
    meta_description = models.CharField(max_length=160, blank=True, verbose_name="توضیحات متا")
    seo_score = models.FloatField(default=0, verbose_name="امتیاز سئو")
    
    # داده‌های ساختاریافته برای گوگل
    schema_markup = models.JSONField(default=dict, blank=True, verbose_name="داده‌های ساختاریافته")
    
    # آمار و بازدید
    views_count = models.PositiveIntegerField(default=0, verbose_name="تعداد بازدید")
    likes_count = models.PositiveIntegerField(default=0, verbose_name="لایک")
    
    # تصاویر
    featured_image = models.ImageField(upload_to='posts/%Y/%m/', blank=True, null=True, verbose_name="تصویر شاخص")
    og_image = models.ImageField(upload_to='og_images/', blank=True, null=True, verbose_name="تصویر اشتراک‌گذاری")
    
    # زمان‌ها
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان انتشار")
    scheduled_for = models.DateTimeField(null=True, blank=True, verbose_name="زمانبندی برای")
    
    # داده‌های تولید خودکار
    generated_by_ai = models.BooleanField(default=False, verbose_name="تولید شده توسط هوش مصنوعی")
    generation_prompt = models.TextField(blank=True, verbose_name="پرامپت تولید")
    ai_model_used = models.CharField(max_length=50, blank=True, verbose_name="مدل AI استفاده شده")
    
    class Meta:
        verbose_name = "پست"
        verbose_name_plural = "پست‌ها"
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['slug']),
            models.Index(fields=['seo_score']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title, allow_unicode=True)
        
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        
        # تولید خودکار خلاصه اگر خالی بود
        if not self.excerpt and self.content:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(self.content, 'html.parser')
            text = soup.get_text()[:200]
            self.excerpt = text + '...' if len(text) >= 200 else text
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('post_detail', args=[self.slug])
    
    def update_seo_score(self):
        """محاسبه امتیاز سئو برای این پست"""
        score = 0
        # طول محتوا
        if len(self.content) > 1000:
            score += 20
        elif len(self.content) > 500:
            score += 10
        
        # وجود کلمه کلیدی در تایتل
        if self.focus_keyword and self.focus_keyword in self.title:
            score += 20
        
        # وجود متا دیسکریپشن
        if self.meta_description:
            score += 15
        
        # وجود تگ‌ها
        if self.tags.count() > 0:
            score += 10
        
        # تصویر شاخص
        if self.featured_image:
            score += 15
        
        # لینک‌های داخلی (می‌تونی پیشرفته‌ترش کنی)
        if 'a href' in self.content:
            score += 10
        
        self.seo_score = score
        self.save(update_fields=['seo_score'])
        return score


class Comment(models.Model):
    """نظرات کاربران"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name="پست")
    author_name = models.CharField(max_length=100, verbose_name="نام")
    author_email = models.EmailField(verbose_name="ایمیل")
    author_website = models.URLField(blank=True, verbose_name="وبسایت")
    content = models.TextField(verbose_name="متن نظر")
    is_approved = models.BooleanField(default=False, verbose_name="تایید شده")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "نظر"
        verbose_name_plural = "نظرات"
        ordering = ['created_at']
    
    def __str__(self):
        return f"نظر {self.author_name} برای {self.post.title}"


class SEOAudit(models.Model):
    """گزارش ممیزی سئو سایت"""
    url = models.CharField(max_length=500, verbose_name="آدرس")
    seo_score = models.FloatField(verbose_name="امتیاز سئو")
    performance_score = models.FloatField(verbose_name="امتیاز عملکرد")
    accessibility_score = models.FloatField(verbose_name="امتیاز دسترسی")
    best_practices_score = models.FloatField(verbose_name="امتیاز بهترین روش‌ها")
    issues = models.JSONField(default=list, verbose_name="مشکلات")
    recommendations = models.JSONField(default=list, verbose_name="توصیه‌ها")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "گزارش ممیزی"
        verbose_name_plural = "گزارش‌های ممیزی"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"ممیزی {self.url} - {self.created_at.strftime('%Y-%m-%d')}"


class GeneratedContentLog(models.Model):
    """لاگ تولید محتوای خودکار"""
    post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name='generation_log', verbose_name="پست")
    source_type = models.CharField(max_length=50, choices=(
        ('trend', 'ترند روز'),
        ('keyword', 'کلمه کلیدی هدف'),
        ('competitor', 'رقبا'),
        ('news', 'اخبار'),
        ('manual', 'دستی'),
    ), verbose_name="نبع تولید")
    source_data = models.JSONField(default=dict, verbose_name="داده منبع")
    generation_time = models.FloatField(verbose_name="زمان تولید (ثانیه)")
    tokens_used = models.IntegerField(default=0, verbose_name="توکن‌های مصرف شده")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "لاگ تولید محتوا"
        verbose_name_plural = "لاگ‌های تولید محتوا"
