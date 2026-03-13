from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InterviewPrepViewSet, JobMatchView, ResumeOptimizerView

router = DefaultRouter()
router.register(r'interview-prep', InterviewPrepViewSet, basename='interview-prep')

urlpatterns = [
    path('', include(router.urls)),
    path('job-match/', JobMatchView.as_view(), name='job-match'),
    path('resume-optimizer/', ResumeOptimizerView.as_view(), name='resume-optimizer'),
]
