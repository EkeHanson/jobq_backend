from rest_framework import serializers
from .models import BlogPost, BlogSubscriber, BlogComment
from django.utils import timezone


class BlogPostSerializer(serializers.ModelSerializer):
    """Serializer for blog posts"""
    
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    comment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'content', 'category', 'category_display',
            'featured_image', 'author_display_picture', 'external_link', 'author', 'author_name', 'is_published', 'is_featured',
            'published_date', 'created_at', 'updated_at', 
            'meta_title', 'meta_description', 'view_count', 'comment_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'view_count']
    
    def get_comment_count(self, obj):
        return obj.comments.filter(is_approved=True).count()


class BlogPostListSerializer(serializers.ModelSerializer):
    """Serializer for blog post list (lighter weight)"""
    
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    comment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'category', 'category_display',
            'featured_image', 'author_display_picture', 'external_link', 'author_name', 'is_featured',
            'published_date', 'created_at', 'view_count', 'comment_count'
        ]
    
    def get_comment_count(self, obj):
        return obj.comments.filter(is_approved=True).count()


class BlogSubscriberSerializer(serializers.ModelSerializer):
    """Serializer for blog subscribers"""
    
    class Meta:
        model = BlogSubscriber
        fields = ['id', 'email', 'is_active', 'subscribed_date', 'source']
        read_only_fields = ['id', 'subscribed_date']
    
    def create(self, validated_data):
        # Check if subscriber already exists
        email = validated_data.get('email')
        subscriber = BlogSubscriber.objects.filter(email=email).first()
        
        if subscriber:
            # Reactivate if previously unsubscribed
            if not subscriber.is_active:
                subscriber.is_active = True
                subscriber.unsubscribed_date = None
                subscriber.save()
            return subscriber
        
        return super().create(validated_data)


class BlogSubscriberCreateSerializer(serializers.Serializer):
    """Serializer for creating/updating subscriptions (no model)"""
    
    email = serializers.EmailField()
    source = serializers.CharField(max_length=50, required=False, default='website')
    
    def validate_email(self, value):
        # Basic email validation
        if not value:
            raise serializers.ValidationError("Email is required")
        return value.lower().strip()
    
    def save(self):
        email = self.validated_data['email']
        source = self.validated_data.get('source', 'website')
        
        subscriber, created = BlogSubscriber.objects.get_or_create(
            email=email,
            defaults={'source': source}
        )
        
        if not created and not subscriber.is_active:
            # Reactivate if previously unsubscribed
            subscriber.is_active = True
            subscriber.unsubscribed_date = None
            subscriber.save()
        
        return subscriber


class BlogCommentSerializer(serializers.ModelSerializer):
    """Serializer for blog comments"""
    
    class Meta:
        model = BlogComment
        fields = [
            'id', 'post', 'author_name', 'author_email', 'content',
            'is_approved', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_approved', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Auto-approve comments for now (can add moderation later)
        validated_data['is_approved'] = True
        return super().create(validated_data)
