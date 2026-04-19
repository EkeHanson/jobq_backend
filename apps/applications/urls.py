from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApplicationViewSet, FollowUpsView, MarkFollowUpSentView, InterviewViewSet, BulkImportView, BulkImportStatusView

router = DefaultRouter()
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'interviews', InterviewViewSet, basename='interview')

urlpatterns = [
    # Custom views (must come before router includes)
    path('applications/followups/', FollowUpsView.as_view(), name='follow-ups'),
    path('applications/followups/mark_sent/', MarkFollowUpSentView.as_view(), name='mark-follow-up-sent'),
    path('applications/bulk-import/', BulkImportView.as_view(), name='bulk-import'),
    path('applications/bulk-import/<uuid:task_id>/', BulkImportStatusView.as_view(), name='bulk-import-status'),
    path('', include(router.urls)),
]
