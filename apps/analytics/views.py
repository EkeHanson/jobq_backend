from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count, Sum
from datetime import timedelta
from django.db.models.functions import TruncDate
import json
from collections import defaultdict

from .models import VisitorSession, PageView, DailyAnalytics
from .serializers import DailyAnalyticsSerializer


class TrackPageView(APIView):
    """API endpoint to track page views"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Get or create session
        session_id = request.data.get('session_id')
        if not session_id:
            return Response({'error': 'session_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get request data
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        path = request.data.get('path', '/')
        title = request.data.get('title', '')
        referrer = request.data.get('referrer', '')
        
        # Parse user agent for device/browser info
        device_type = 'desktop'
        browser = 'unknown'
        os = 'unknown'
        
        if user_agent:
            user_agent_lower = user_agent.lower()
            if 'mobile' in user_agent_lower or 'android' in user_agent_lower:
                device_type = 'mobile'
            elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
                device_type = 'tablet'
            
            if 'chrome' in user_agent_lower:
                browser = 'chrome'
            elif 'firefox' in user_agent_lower:
                browser = 'firefox'
            elif 'safari' in user_agent_lower:
                browser = 'safari'
            elif 'edge' in user_agent_lower:
                browser = 'edge'
            
            if 'windows' in user_agent_lower:
                os = 'windows'
            elif 'mac' in user_agent_lower:
                os = 'macos'
            elif 'linux' in user_agent_lower:
                os = 'linux'
            elif 'android' in user_agent_lower:
                os = 'android'
            elif 'ios' in user_agent_lower or 'iphone' in user_agent_lower:
                os = 'ios'
        
        # Get or create session
        session, created = VisitorSession.objects.get_or_create(
            session_id=session_id,
            defaults={
                'ip_address': ip_address,
                'user_agent': user_agent,
                'device_type': device_type,
                'browser': browser,
                'os': os,
                'referrer': referrer,
                'is_new_visitor': True,
            }
        )
        
        # Update last seen
        session.last_seen = timezone.now()
        if created:
            session.is_new_visitor = True
        session.save()
        
        # Create page view
        PageView.objects.create(
            session=session,
            path=path,
            title=title,
        )
        
        # Update daily analytics (async in production, sync for now)
        self.update_daily_analytics()
        
        return Response({'status': 'tracked'})
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def update_daily_analytics(self):
        """Update daily analytics summary"""
        today = timezone.now().date()
        
        # Get today's data
        sessions = VisitorSession.objects.filter(last_seen__date=today)
        page_views = PageView.objects.filter(timestamp__date=today)
        
        # Calculate unique visitors (sessions that viewed pages)
        unique_visitors = page_views.values('session').distinct().count()
        new_visitors = sessions.filter(is_new_visitor=True).count()
        
        # Demographics
        mobile_visitors = sessions.filter(device_type='mobile').count()
        desktop_visitors = sessions.filter(device_type='desktop').count()
        tablet_visitors = sessions.filter(device_type='tablet').count()
        
        # Top referrers
        referrer_counts = sessions.exclude(referrer='').values('referrer').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        top_referrers = {r['referrer']: r['count'] for r in referrer_counts}
        
        # Top pages
        page_counts = page_views.values('path').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        top_pages = {p['path']: p['count'] for p in page_counts}
        
        # Top countries
        country_counts = sessions.exclude(country__isnull=True).exclude(country='').values(
            'country'
        ).annotate(count=Count('id')).order_by('-count')[:10]
        top_countries = {c['country']: c['count'] for c in country_counts}
        
        # Update or create daily analytics
        DailyAnalytics.objects.update_or_create(
            date=today,
            defaults={
                'total_visitors': sessions.count(),
                'unique_visitors': unique_visitors,
                'new_visitors': new_visitors,
                'returning_visitors': unique_visitors - new_visitors,
                'total_page_views': page_views.count(),
                'mobile_visitors': mobile_visitors,
                'desktop_visitors': desktop_visitors,
                'tablet_visitors': tablet_visitors,
                'top_referrers': top_referrers,
                'top_pages': top_pages,
                'top_countries': top_countries,
            }
        )


class AnalyticsOverviewView(generics.ListAPIView):
    """Get analytics overview"""
    serializer_class = DailyAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        days = self.request.query_params.get('days', 30)
        try:
            days = int(days)
        except ValueError:
            days = 30
        
        start_date = timezone.now().date() - timedelta(days=days)
        return DailyAnalytics.objects.filter(date__gte=start_date).order_by('-date')


class AnalyticsSummaryView(APIView):
    """Get analytics summary with totals"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        days = request.query_params.get('days', 30)
        try:
            days = int(days)
        except ValueError:
            days = 30
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        # Get analytics for the period
        analytics = DailyAnalytics.objects.filter(date__gte=start_date)
        
        # Calculate totals
        total_visitors = analytics.aggregate(Sum('total_visitors'))['total_visitors__sum'] or 0
        unique_visitors = analytics.aggregate(Sum('unique_visitors'))['unique_visitors__sum'] or 0
        new_visitors = analytics.aggregate(Sum('new_visitors'))['new_visitors__sum'] or 0
        total_page_views = analytics.aggregate(Sum('total_page_views'))['total_page_views__sum'] or 0
        
        # Device breakdown
        mobile = analytics.aggregate(Sum('mobile_visitors'))['mobile_visitors__sum'] or 0
        desktop = analytics.aggregate(Sum('desktop_visitors'))['desktop_visitors__sum'] or 0
        tablet = analytics.aggregate(Sum('tablet_visitors'))['tablet_visitors__sum'] or 0
        
        # Daily data for chart
        daily_data = list(analytics.values('date', 'unique_visitors', 'total_page_views', 'new_visitors'))
        
        return Response({
            'period_days': days,
            'totals': {
                'visitors': total_visitors,
                'unique_visitors': unique_visitors,
                'new_visitors': new_visitors,
                'page_views': total_page_views,
            },
            'devices': {
                'mobile': mobile,
                'desktop': desktop,
                'tablet': tablet,
            },
            'daily': daily_data,
        })
