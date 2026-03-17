from django.urls import path
from .views import TrackPageView, AnalyticsOverviewView, AnalyticsSummaryView

urlpatterns = [
    path('track/', TrackPageView.as_view(), name='track-page-view'),
    path('overview/', AnalyticsOverviewView.as_view(), name='analytics-overview'),
    path('summary/', AnalyticsSummaryView.as_view(), name='analytics-summary'),
]
