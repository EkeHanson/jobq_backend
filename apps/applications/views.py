from rest_framework import viewsets, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from django.utils import timezone

from .models import Application, StatusHistory
from .serializers import ApplicationSerializer, StatusHistorySerializer


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.select_related('user').prefetch_related('history').all().order_by('-created_at')
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not self.request.user.is_staff:
            qs = qs.filter(user=user)
        
        # Filter by archived status - show all by default
        archived = self.request.query_params.get('archived')
        if archived is not None:
            qs = qs.filter(archived=archived.lower() == 'true')
        # No filter param = show all (both active and archived)
        
        # Filter out soft-deleted applications by default
        # Include deleted if explicitly requested
        include_deleted = self.request.query_params.get('include_deleted', 'false').lower() == 'true'
        if not include_deleted:
            qs = qs.filter(deleted_at__isnull=True)
        
        return qs
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get application statistics for current user"""
        qs = Application.objects.filter(user=request.user)
        total = qs.count()
        
        # Use Django aggregation for efficient status counting - O(1) instead of O(n)
        status_counts = qs.values('status').annotate(count=Count('id'))
        by_status = {item['status'] or 'unknown': item['count'] for item in status_counts}
        
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
            'archived_count': qs.filter(archived=True).count(),
        }
        return Response(stats)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive an application"""
        application = self.get_object()
        application.archived = True
        application.archived_at = timezone.now()
        application.save()
        return Response({'status': 'archived', 'archived_at': application.archived_at})

    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Unarchive an application"""
        application = self.get_object()
        application.archived = False
        application.archived_at = None
        application.save()
        return Response({'status': 'unarchived'})

    @action(detail=True, methods=['post'])
    def soft_delete(self, request, pk=None):
        """Soft delete an application"""
        application = self.get_object()
        application.deleted_at = timezone.now()
        application.save()
        return Response({'status': 'deleted', 'deleted_at': application.deleted_at})

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted application"""
        application = self.get_object()
        application.deleted_at = None
        application.save()
        return Response({'status': 'restored'})


class StatusHistoryView(generics.ListAPIView):
    serializer_class = StatusHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        application_id = self.kwargs['pk']
        return StatusHistory.objects.filter(application_id=application_id)
