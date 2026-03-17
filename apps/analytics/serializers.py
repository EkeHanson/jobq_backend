from rest_framework import serializers
from .models import VisitorSession, PageView, DailyAnalytics


class PageViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageView
        fields = ['id', 'session', 'path', 'title', 'timestamp', 'time_on_page']


class VisitorSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorSession
        fields = ['id', 'session_id', 'ip_address', 'country', 'region', 'city', 
                  'device_type', 'browser', 'os', 'referrer', 'first_seen', 'last_seen', 'is_new_visitor']


class DailyAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyAnalytics
        fields = ['id', 'date', 'total_visitors', 'unique_visitors', 'new_visitors', 
                  'returning_visitors', 'total_page_views', 'mobile_visitors', 
                  'desktop_visitors', 'tablet_visitors', 'top_referrers', 'top_pages', 'top_countries']
