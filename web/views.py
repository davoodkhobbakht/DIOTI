#web/views.py

from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.contrib.sitemaps import Sitemap
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView
from .models import Post, Category, Tag, Comment
from django.contrib import messages
from django.shortcuts import redirect
from .forms import CommentForm, SearchForm, ContactForm, NewsletterForm
from django.utils import timezone


class HomeView(ListView):
    """صفحه اصلی با لیست پست‌ها"""
    model = Post
    template_name = 'web/home.html'
    context_object_name = 'posts'
    paginate_by = 9
    
    def get_queryset(self):
        return Post.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).select_related('category').prefetch_related('tags').order_by('-published_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # پست‌های ویژه (پربازدیدترین)
        context['featured_posts'] = Post.objects.filter(
            status='published'
        ).order_by('-views_count')[:5]
        
        # دسته‌بندی‌های پرکاربرد
        context['top_categories'] = Category.objects.filter(
            is_active=True,
            posts__status='published'
        ).annotate(post_count=Count('posts')).order_by('-post_count')[:8]
        
        # تبلیغات سایدبار
        context['sidebar_ads'] = [
            {'title': 'تبلیغات ویژه 1', 'code': '<!-- Ad Code 1 -->'},
            {'title': 'تبلیغات ویژه 2', 'code': '<!-- Ad Code 2 -->'},
        ]
        
        return context



class PostDetailView(DetailView):
    """نمایش جزئیات یک پست با فرم نظر"""
    model = Post
    template_name = 'web/post_detail.html'
    context_object_name = 'post'
    
    def get_object(self):
        obj = super().get_object()
        obj.views_count += 1
        obj.save(update_fields=['views_count'])
        return obj
    
    def get_queryset(self):
        return Post.objects.filter(status='published').select_related('category').prefetch_related('tags', 'comments')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        
        context['related_posts'] = Post.objects.filter(
            category=post.category, status='published'
        ).exclude(id=post.id)[:4]
        
        context['comments'] = post.comments.filter(is_approved=True)
        context['comment_form'] = CommentForm(post=post)
        context['search_form'] = SearchForm()
        
        return context
    
    def post(self, request, *args, **kwargs):
        """پردازش ارسال نظر"""
        self.object = self.get_object()
        form = CommentForm(request.POST, post=self.object)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = self.object
            comment.user_ip = request.META.get('REMOTE_ADDR')
            comment.save()
            
            messages.success(request, 'نظر شما با موفقیت ثبت شد. پس از تایید نمایش داده می‌شود.')
            return redirect(self.object.get_absolute_url())
        else:
            messages.error(request, 'خطا در ثبت نظر. لطفا دوباره تلاش کنید.')
            return self.get(request, *args, **kwargs)


class CategoryView(ListView):
    """نمایش پست‌های یک دسته‌بندی"""
    template_name = 'web/category.html'
    context_object_name = 'posts'
    paginate_by = 9
    
    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'], is_active=True)
        return Post.objects.filter(
            category=self.category,
            status='published'
        ).order_by('-published_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class TagView(ListView):
    """نمایش پست‌های یک برچسب"""
    template_name = 'web/tag.html'
    context_object_name = 'posts'
    paginate_by = 9
    
    def get_queryset(self):
        self.tag = get_object_or_404(Tag, slug=self.kwargs['slug'])
        return self.tag.posts.filter(status='published').order_by('-published_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        return context


class SearchView(ListView):
    """جستجوی پیشرفته"""
    template_name = 'web/search.html'
    context_object_name = 'posts'
    paginate_by = 9
    
    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        if not query:
            return Post.objects.none()
        
        return Post.objects.filter(
            Q(status='published'),
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(focus_keyword__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct().order_by('-seo_score', '-published_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


def about_page(request):
    """صفحه درباره ما"""
    return render(request, 'web/about.html', {
        'team_members': [
            {'name': 'دیوود خوببخت', 'role': 'توسعه‌دهنده ارشد', 'bio': 'متخصص سئو و هوش مصنوعی'},
        ]
    })


def contact_page(request):
    """صفحه تماس با ما با پردازش فرم"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # ارسال ایمیل یا ذخیره در دیتابیس
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            # اینجا می‌توانی ایمیل بفرستی یا در دیتابیس ذخیره کنی
            # send_contact_email(name, email, subject, message)
            
            messages.success(request, 'پیام شما با موفقیت ارسال شد. به زودی با شما تماس می‌گیریم.')
            return redirect('contact')
        else:
            messages.error(request, 'خطا در ارسال پیام. لطفا دوباره تلاش کنید.')
    else:
        form = ContactForm()
    
    return render(request, 'web/contact.html', {'form': form, 'search_form': SearchForm()})


def robots_txt(request):
    """فایل robots.txt برای سئو"""
    lines = [
        "User-Agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Sitemap: https://yourdomain.com/sitemap.xml",
        "Host: yourdomain.com",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def newsletter_subscribe(request):
    """عضویت در خبرنامه (AJAX)"""
    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            # ذخیره در دیتابیس یا سرویس خبرنامه
            # Subscriber.objects.create(email=email)
            return JsonResponse({'status': 'success', 'message': 'عضویت با موفقیت انجام شد.'})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر'}, status=400)
# Sitemap برای گوگل
class PostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    
    def items(self):
        return Post.objects.filter(status='published')
    
    def lastmod(self, obj):
        return obj.updated_at
    
    def location(self, obj):
        return obj.get_absolute_url()


class CategorySitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5
    
    def items(self):
        return Category.objects.filter(is_active=True)

