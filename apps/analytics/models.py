from django.db import models
from django.conf import settings
import uuid
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class VisitorSession(models.Model):
    """Tracks unique visitor sessions"""
    session_id = models.UUIDField(default=uuid.uuid4, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    # Demographics
    country = models.CharField(max_length=2, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    device_type = models.CharField(max_length=20, null=True, blank=True)  # mobile, tablet, desktop
    browser = models.CharField(max_length=50, null=True, blank=True)
    os = models.CharField(max_length=50, null=True, blank=True)
    
    # Referrer tracking
    referrer = models.URLField(null=True, blank=True)
    utm_source = models.CharField(max_length=100, null=True, blank=True)
    utm_medium = models.CharField(max_length=100, null=True, blank=True)
    utm_campaign = models.CharField(max_length=100, null=True, blank=True)
    
    # Timestamps
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_new_visitor = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-last_seen']
    
    def __str__(self):
        return f"Session {self.session_id} - {self.country or 'Unknown'}"


class PageView(models.Model):
    """Tracks individual page views"""
    session = models.ForeignKey(VisitorSession, on_delete=models.CASCADE, related_name='page_views')
    path = models.CharField(max_length=500)
    title = models.CharField(max_length=500, null=True, blank=True)
    query_params = models.CharField(max_length=500, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    time_on_page = models.IntegerField(null=True, blank=True)  # seconds
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.path} - {self.timestamp}"


class DailyAnalytics(models.Model):
    """Aggregated daily analytics for quick reporting"""
    date = models.DateField(unique=True)
    
    # Visitor counts
    total_visitors = models.IntegerField(default=0)
    unique_visitors = models.IntegerField(default=0)
    new_visitors = models.IntegerField(default=0)
    returning_visitors = models.IntegerField(default=0)
    
    # Page views
    total_page_views = models.IntegerField(default=0)
    
    # Demographics
    mobile_visitors = models.IntegerField(default=0)
    desktop_visitors = models.IntegerField(default=0)
    tablet_visitors = models.IntegerField(default=0)
    
    # Top referrers (stored as JSON)
    top_referrers = models.JSONField(default=dict)
    
    # Top pages (stored as JSON)
    top_pages = models.JSONField(default=dict)
    
    # Countries (stored as JSON)
    top_countries = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"Analytics for {self.date}"
