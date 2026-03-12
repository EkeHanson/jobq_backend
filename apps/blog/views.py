from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser, AllowAny
from django.db.models import Q
from django.utils import timezone

from .models import BlogPost, BlogSubscriber, BlogComment
from .serializers import (
    BlogPostSerializer, 
    BlogPostListSerializer, 
    BlogSubscriberSerializer,
    BlogSubscriberCreateSerializer,
    BlogCommentSerializer
)


class BlogPostViewSet(viewsets.ModelViewSet):
    """ViewSet for blog posts"""
    
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BlogPostListSerializer
        return BlogPostSerializer
    
    def get_queryset(self):
        queryset = BlogPost.objects.filter(is_published=True)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter featured posts
        featured = self.request.query_params.get('featured')
        if featured and featured.lower() == 'true':
            queryset = queryset.filter(is_featured=True)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(content__icontains=search) |
                Q(excerpt__icontains=search)
            )
        
        return queryset.select_related('author')
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count
        instance.increment_views()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    # Admin actions
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def all(self, request):
        """Get all posts including unpublished (admin only)"""
        queryset = BlogPost.objects.all().select_related('author')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def feature(self, request, slug=None):
        """Toggle featured status"""
        post = self.get_object()
        post.is_featured = not post.is_featured
        post.save()
        serializer = self.get_serializer(post)
        return Response(serializer.data)


class BlogSubscriberViewSet(viewsets.ModelViewSet):
    """ViewSet for blog subscribers (admin only)"""
    
    serializer_class = BlogSubscriberSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'email'
    
    def get_queryset(self):
        queryset = BlogSubscriber.objects.all()
        
        # Filter by status
        active = self.request.query_params.get('active')
        if active:
            is_active = active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        return queryset
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def subscribe(self, request):
        """Subscribe to blog updates"""
        serializer = BlogSubscriberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscriber = serializer.save()
        
        return Response({
            'message': 'Successfully subscribed to blog updates!',
            'email': subscriber.email
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def unsubscribe(self, request):
        """Unsubscribe from blog updates"""
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            subscriber = BlogSubscriber.objects.get(email=email.lower())
            subscriber.is_active = False
            subscriber.unsubscribed_date = timezone.now()
            subscriber.save()
            
            return Response({'message': 'Successfully unsubscribed from blog updates'})
        except BlogSubscriber.DoesNotExist:
            return Response(
                {'message': 'Email not found. You may already be unsubscribed.'},
                status=status.HTTP_200_OK
            )
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def status(self, request):
        """Check subscription status"""
        email = request.query_params.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            subscriber = BlogSubscriber.objects.get(email=email)
            return Response({
                'email': subscriber.email,
                'is_active': subscriber.is_active,
                'subscribed_date': subscriber.subscribed_date
            })
        except BlogSubscriber.DoesNotExist:
            return Response({
                'email': email,
                'is_active': False,
                'subscribed': False
            })


class BlogCommentViewSet(viewsets.ModelViewSet):
    """ViewSet for blog comments"""
    
    serializer_class = BlogCommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        return BlogComment.objects.filter(
            post__slug=self.kwargs['post_slug'],
            is_approved=True
        ).select_related('post')
    
    def perform_create(self, serializer):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # If user is authenticated, use their info
        if self.request.user.is_authenticated:
            serializer.save(
                author_name=self.request.user.get_full_name() or self.request.user.username,
                author_email=self.request.user.email
            )
        else:
            serializer.save()
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {'message': 'Comment posted successfully!'},
            status=status.HTTP_201_CREATED
        )


class FeaturedPostsView(generics.ListAPIView):
    """Get featured blog posts"""
    
    serializer_class = BlogPostListSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return BlogPost.objects.filter(
            is_published=True,
            is_featured=True
        ).select_related('author')[:5]


class LatestPostsView(generics.ListAPIView):
    """Get latest blog posts"""
    
    serializer_class = BlogPostListSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        limit = int(self.request.query_params.get('limit', 10))
        # Cap limit to prevent excessive queries
        limit = min(limit, 50)
        return BlogPost.objects.filter(
            is_published=True
        ).select_related('author')[:limit]
