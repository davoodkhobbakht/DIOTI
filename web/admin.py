#web/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Category, Post, Tag, Comment, SEOAudit, GeneratedContentLog

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'post_count', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    def post_count(self, obj):
        return obj.posts.filter(status='published').count()
    post_count.short_description = "تعداد پست‌ها"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'post_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    def post_count(self, obj):
        return obj.posts.count()
    post_count.short_description = "تعداد پست‌ها"


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title_preview', 'category', 'post_type', 'status_badge', 'seo_score_badge', 'views_count', 'published_at']
    list_filter = ['status', 'post_type', 'category', 'generated_by_ai', 'created_at']
    search_fields = ['title', 'content', 'focus_keyword']
    readonly_fields = ['seo_score', 'views_count', 'created_at', 'updated_at',]
   
    date_hierarchy = 'published_at'
    actions = ['publish_selected', 'calculate_seo_scores']
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title',  'category', 'tags', 'content', 'excerpt', 'featured_image')
        }),
        ('وضعیت و نوع', {
            'fields': ('post_type', 'status', 'scheduled_for')
        }),
        ('سئو و بهینه‌سازی', {
            'fields': ('focus_keyword', 'meta_description', 'seo_score', 'schema_markup')
        }),
        ('داده‌های AI', {
            'classes': ('collapse',),
            'fields': ('generated_by_ai', 'generation_prompt', 'ai_model_used')
        }),
        ('آمار', {
            'fields': ('views_count', 'likes_count', 'created_at', 'updated_at', 'published_at')
        }),
    )
    
    def title_preview(self, obj):
        return format_html('<a href="{}" target="_blank">{}</a>', obj.get_absolute_url(), obj.title[:50])
    title_preview.short_description = "عنوان"
    
    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'published': 'green',
            'scheduled': 'orange',
            'trash': 'red',
        }
        return format_html('<span style="color: {};">●</span> {}', colors.get(obj.status, 'black'), obj.get_status_display())
    status_badge.short_description = "وضعیت"
    
    def seo_score_badge(self, obj):
        color = 'red' if obj.seo_score < 50 else 'orange' if obj.seo_score < 70 else 'green'
        return format_html('<span style="color: {}; font-weight: bold;">{}/100</span>', color, obj.seo_score)
    seo_score_badge.short_description = "امتیاز سئو"
    
    def publish_selected(self, request, queryset):
        updated = queryset.update(status='published', published_at=timezone.now())
        self.message_user(request, f'{updated} پست با موفقیت منتشر شد.')
    publish_selected.short_description = "انتشار انتخاب‌شده‌ها"
    
    def calculate_seo_scores(self, request, queryset):
        for post in queryset:
            post.update_seo_score()
        self.message_user(request, 'امتیاز سئو برای پست‌های انتخاب‌شده محاسبه شد.')
    calculate_seo_scores.short_description = "محاسبه امتیاز سئو"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author_name', 'post', 'content_preview', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['author_name', 'author_email', 'content']
    actions = ['approve_comments']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = "متن نظر"
    
    def approve_comments(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} نظر تایید شد.')
    approve_comments.short_description = "تایید نظرات انتخاب‌شده"


@admin.register(SEOAudit)
class SEOAuditAdmin(admin.ModelAdmin):
    list_display = ['url', 'seo_score', 'performance_score', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['url', 'seo_score', 'performance_score', 'accessibility_score', 'best_practices_score', 'issues', 'recommendations']
    
    def has_add_permission(self, request):
        return False

