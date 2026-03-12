from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InterviewPrepViewSet

router = DefaultRouter()
router.register(r'interview-prep', InterviewPrepViewSet, basename='interview-prep')

urlpatterns = [
    path('', include(router.urls)),
]
