from django.contrib import admin
from django.urls import path, include
from rest_framework import routers

from apps.jobs import views as job_views
from apps.applications import views as app_views
from apps.notifications import views as notification_views
from apps.profiles import views as profile_views
from apps.subscriptions import views as subscription_views
from apps.ai import views as ai_views

router = routers.DefaultRouter()
router.register(r'jobs', job_views.JobViewSet, basename='job')
router.register(r'companies', job_views.CompanyViewSet, basename='company')
router.register(r'interviews', app_views.InterviewViewSet, basename='interview')
router.register(r'notifications', notification_views.NotificationViewSet, basename='notification')
router.register(r'contact', notification_views.ContactMessageViewSet, basename='contact')
router.register(r'reviews', notification_views.ReviewViewSet, basename='review')
router.register(r'profiles', profile_views.ProfileViewSet, basename='profile')
router.register(r'subscription', subscription_views.SubscriptionViewSet, basename='subscription')
router.register(r'ai/interview-prep', ai_views.InterviewPrepViewSet, basename='interview-prep')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.users.urls')),
    # Applications endpoints
    path('api/v1/', include('apps.applications.urls')),
    # Insights (formerly Blog) endpoints
    path('api/v1/insights/', include('apps.blog.urls')),
    # Analytics endpoints
    path('api/v1/analytics/', include('apps.analytics.urls')),
    # Custom views (must come before router includes)
    path('api/v1/jobs/extract/', job_views.JobExtractView.as_view(), name='job-extract'),
    path('api/v1/jobs/extract/status/<uuid:task_id>/', job_views.JobExtractStatusView.as_view(), name='job-extract-status'),
    path('api/v1/jobs/extract/result/<uuid:task_id>/', job_views.JobExtractResultView.as_view(), name='job-extract-result'),
    # subscription invoices
    path('api/v1/subscription/invoices/', subscription_views.InvoiceListView.as_view(), name='invoice-list'),
    path('api/v1/subscription/invoices/<int:invoice_id>/download/', subscription_views.InvoiceDownloadView.as_view(), name='invoice-download'),
    # Public subscription plans (no auth required)
    path('api/v1/subscription/plans/', subscription_views.public_subscription_plans, name='public-subscription-plans'),
    # Router URLs last
    path('api/v1/', include(router.urls)),
]

# serve media in development
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
