from django.contrib import admin
from .models import VisitorSession, PageView, DailyAnalytics


@admin.register(VisitorSession)
class VisitorSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'country', 'device_type', 'browser', 'os', 'first_seen', 'last_seen', 'is_new_visitor']
    list_filter = ['device_type', 'browser', 'os', 'country', 'is_new_visitor']
    search_fields = ['session_id', 'ip_address', 'country', 'region', 'city']
    readonly_fields = ['session_id', 'first_seen', 'last_seen']
    date_hierarchy = 'last_seen'


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ['path', 'session', 'title', 'timestamp']
    list_filter = ['path', 'timestamp']
    search_fields = ['path', 'title', 'session__session_id']
    readonly_fields = ['session', 'path', 'title', 'timestamp']
    date_hierarchy = 'timestamp'


@admin.register(DailyAnalytics)
class DailyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_visitors', 'unique_visitors', 'new_visitors', 'total_page_views', 'mobile_visitors', 'desktop_visitors']
    list_filter = ['date']
    readonly_fields = ['date', 'total_visitors', 'unique_visitors', 'new_visitors', 'returning_visitors', 
                      'total_page_views', 'mobile_visitors', 'desktop_visitors', 'tablet_visitors',
                      'top_referrers', 'top_pages', 'top_countries']
    date_hierarchy = 'date'
