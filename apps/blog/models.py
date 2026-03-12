from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
import uuid


class BlogPost(models.Model):
    """Blog post model for news and articles"""
    
    CATEGORY_CHOICES = [
        ('job_search', 'Job Search'),
        ('career_advice', 'Career Advice'),
        ('technology', 'Technology'),
        ('interviews', 'Interviews'),
        ('personal_branding', 'Personal Branding'),
        ('salary', 'Salary & Compensation'),
        ('remote_work', 'Remote Work'),
        ('industry_news', 'Industry News'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    excerpt = models.TextField(max_length=500, help_text="Short summary for the card view")
    content = models.TextField(help_text="Full article content (HTML or Markdown supported)")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='career_advice')
    featured_image = models.URLField(blank=True, help_text="URL to the featured image")
    author_display_picture = models.URLField(blank=True, help_text="URL to the author's display picture/avatar")
    external_link = models.URLField(blank=True, help_text="Optional external link (for linking to external articles)")
    
    author = models.ForeignKey(
        get_user_model(), 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='blog_posts'
    )
    
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, help_text="Show in featured section")
    
    published_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # SEO
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    
    view_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-published_date', '-created_at']
        verbose_name = 'Insight'
        verbose_name_plural = 'Insights'
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # Ensure unique slug
            original_slug = self.slug
            counter = 1
            while BlogPost.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        if self.is_published and not self.published_date:
            from django.utils import timezone
            self.published_date = timezone.now()
        
        super().save(*args, **kwargs)
    
    def increment_views(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])


class BlogSubscriber(models.Model):
    """Email subscription for blog updates"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    
    subscribed_date = models.DateTimeField(auto_now_add=True)
    unsubscribed_date = models.DateTimeField(null=True, blank=True)
    
    # Track subscription source
    source = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Where the user subscribed from"
    )
    
    class Meta:
        ordering = ['-subscribed_date']
        verbose_name = 'Insight Subscriber'
        verbose_name_plural = 'Insight Subscribers'
    
    def __str__(self):
        return self.email


class BlogComment(models.Model):
    """Comments on blog posts"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments')
    
    author_name = models.CharField(max_length=100)
    author_email = models.EmailField()
    content = models.TextField(max_length=1000)
    
    is_approved = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Insight Comment'
        verbose_name_plural = 'Insight Comments'
    
    def __str__(self):
        return f"Comment by {self.author_name} on {self.post.title}"
