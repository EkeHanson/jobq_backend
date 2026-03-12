from django.contrib import admin
from .models import BlogPost, BlogSubscriber, BlogComment


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'author', 'is_published', 'is_featured', 'published_date', 'view_count']
    list_filter = ['is_published', 'is_featured', 'category', 'published_date']
    search_fields = ['title', 'content', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_date'
    ordering = ['-published_date']
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'excerpt', 'content', 'category', 'featured_image', 'external_link')
        }),
        ('Author', {
            'fields': ('author', 'author_display_picture')
        }),
        ('Status', {
            'fields': ('is_published', 'is_featured', 'published_date')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['view_count', 'created_at', 'updated_at']


@admin.register(BlogSubscriber)
class BlogSubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'is_active', 'subscribed_date', 'unsubscribed_date', 'source']
    list_filter = ['is_active', 'subscribed_date']
    search_fields = ['email']
    date_hierarchy = 'subscribed_date'
    ordering = ['-subscribed_date']


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ['author_name', 'post', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['author_name', 'author_email', 'content']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    actions = ['approve_comments', 'disapprove_comments']
    
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
    approve_comments.short_description = 'Approve selected comments'
    
    def disapprove_comments(self, request, queryset):
        queryset.update(is_approved=False)
    disapprove_comments.short_description = 'Disapprove selected comments'
