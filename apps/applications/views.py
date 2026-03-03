from rest_framework import viewsets, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count

from .models import Application, StatusHistory
from .serializers import ApplicationSerializer, StatusHistorySerializer


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all().order_by('-created_at')
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not self.request.user.is_staff:
            qs = qs.filter(user=user)
        return qs
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get application statistics for current user"""
        qs = Application.objects.filter(user=request.user)
        total = qs.count()
        by_status = {}
        for app in qs:
            status = app.status or 'unknown'
            by_status[status] = by_status.get(status, 0) + 1
        
        total_companies = qs.values('company_name').distinct().count()
        
        interview_rate = (by_status.get('interview', 0) / total * 100) if total else 0
        offer_rate = (by_status.get('offer', 0) / total * 100) if total else 0
        response_rate = (
            (by_status.get('interview', 0) + by_status.get('offer', 0) + by_status.get('rejected', 0))
            / total * 100
        ) if total else 0
        
        stats = {
            'total': total,
            'total_companies': total_companies,
            'by_status': by_status,
            'response_rate': response_rate,
            'interview_rate': interview_rate,
            'offer_rate': offer_rate,
        }
        return Response(stats)


class StatusHistoryView(generics.ListAPIView):
    serializer_class = StatusHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        application_id = self.kwargs['pk']
        return StatusHistory.objects.filter(application_id=application_id)
