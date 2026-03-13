from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JobViewSet, CompanyViewSet, JobExtractView, JobExtractStatusView, JobExtractResultView, JobAggregationView

router = DefaultRouter()
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'companies', CompanyViewSet, basename='company')

urlpatterns = [
    path('', include(router.urls)),
    path('extract/', JobExtractView.as_view(), name='job-extract'),
    path('extract/<str:task_id>/', JobExtractStatusView.as_view(), name='job-extract-status'),
    path('result/<str:task_id>/', JobExtractResultView.as_view(), name='job-extract-result'),
    path('aggregate/', JobAggregationView.as_view(), name='job-aggregate'),
]
