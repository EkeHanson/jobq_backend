from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApplicationViewSet, FollowUpsView, InterviewViewSet

router = DefaultRouter()
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'interviews', InterviewViewSet, basename='interview')

urlpatterns = [
    # Custom views (must come before router includes)
    path('applications/followups/', FollowUpsView.as_view(), name='follow-ups'),
    path('', include(router.urls)),
]
