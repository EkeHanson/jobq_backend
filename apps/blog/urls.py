from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BlogPostViewSet, 
    BlogSubscriberViewSet, 
    BlogCommentViewSet,
    FeaturedPostsView,
    LatestPostsView
)

app_name = 'insights'

router = DefaultRouter()
router.register(r'posts', BlogPostViewSet, basename='insights-post')
router.register(r'subscribers', BlogSubscriberViewSet, basename='insights-subscriber')
router.register(r'posts/(?P<post_slug>[^/.]+)/comments', BlogCommentViewSet, basename='insights-comment')

urlpatterns = [
    path('', include(router.urls)),
    path('featured/', FeaturedPostsView.as_view(), name='featured-posts'),
    path('latest/', LatestPostsView.as_view(), name='latest-posts'),
]
