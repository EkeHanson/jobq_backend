from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Count, Sum, Q
from datetime import timedelta

from .models import User, StaffAssignment, JobPosterStats
from .serializers_assignment import (  # We'll create this next
    StaffAssignmentSerializer,
    JobPosterStatsSerializer,
    UserStaffAssignmentSerializer,
)


class StaffAssignmentViewSet(viewsets.ModelViewSet):
    """Manage staff assignments for job posting users"""
    queryset = StaffAssignment.objects.all()
    serializer_class = StaffAssignmentSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = []
    
    def get_queryset(self):
        qs = super().get_queryset().select_related('staff', 'user')
        
        # Filter by active status
        active = self.request.query_params.get('active')
        if active is not None:
            is_active = active.lower() == 'true'
            qs = qs.filter(is_active=is_active)
        
        # Filter by staff member
        staff_id = self.request.query_params.get('staff_id')
        if staff_id:
            qs = qs.filter(staff_id=staff_id)
        
        # Filter by assigned user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)
        
        return qs
    
    def create(self, request, *args, **kwargs):
        """Create a staff assignment"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        staff = serializer.validated_data['staff']
        user = serializer.validated_data['user']
        
        # Check if staff member is actually a staff user
        if not staff.is_staff:
            return Response(
                {'detail': 'Assigned staff member must have is_staff=True'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if assignment already exists
        if StaffAssignment.objects.filter(staff=staff, user=user, is_active=True).exists():
            # Reactivate if exists
            assignment = StaffAssignment.objects.get(staff=staff, user=user)
            assignment.is_active = True
            assignment.save()
            serializer = self.get_serializer(assignment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a staff assignment"""
        assignment = self.get_object()
        assignment.is_active = False
        assignment.save()
        return Response({'status': 'deactivated'})
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Reactivate a staff assignment"""
        assignment = self.get_object()
        assignment.is_active = True
        assignment.save()
        return Response({'status': 'activated'})


class JobPosterStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """View job poster statistics"""
    queryset = JobPosterStats.objects.all()
    serializer_class = JobPosterStatsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = []
    
    def get_queryset(self):
        qs = super().get_queryset().select_related('user')
        
        # Staff can view all stats, regular users can only view their own
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        
        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id and self.request.user.is_staff:
            qs = qs.filter(user_id=user_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            # Note: This is a simplified filter - in production you'd parse dates properly
            pass
        
        return qs
    
    @action(detail=False, methods=['get'])
    def dashboard_summary(self, request):
        """Get summary statistics for the dashboard"""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Staff access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        total_users = User.objects.filter(is_staff_poster=True).count()
        total_jobs_posted = JobPosterStats.objects.aggregate(
            total=Sum('total_jobs_posted')
        )['total'] or 0
        total_jobs_approved = JobPosterStats.objects.aggregate(
            total=Sum('total_jobs_approved')
        )['total'] or 0
        total_jobs_rejected = JobPosterStats.objects.aggregate(
            total=Sum('total_jobs_rejected')
        )['total'] or 0
        total_jobs_pending = JobPosterStats.objects.aggregate(
            total=Sum('total_jobs_pending')
        )['total'] or 0
        total_applications = JobPosterStats.objects.aggregate(
            total=Sum('total_applications_received')
        )['total'] or 0
        
        # Top performers
        top_performers = JobPosterStats.objects.select_related('user').order_by(
            '-total_jobs_posted'
        )[:5]
        
        top_performers_data = [
            {
                'user_id': stat.user.id,
                'username': stat.user.username,
                'email': stat.user.email,
                'total_jobs_posted': stat.total_jobs_posted,
                'total_jobs_approved': stat.total_jobs_approved,
                'total_jobs_rejected': stat.total_jobs_rejected,
                'approval_rate': round(
                    (stat.total_jobs_approved / stat.total_jobs_posted * 100) 
                    if stat.total_jobs_posted > 0 else 0, 1
                ),
                'total_applications': stat.total_applications_received,
            }
            for stat in top_performers
        ]
        
        # Activity this week
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        from apps.jobs.models import Job
        weekly_jobs = Job.objects.filter(
            posted_at__date__gte=week_ago
        ).count()
        
        return Response({
            'total_poster_users': total_users,
            'total_jobs_posted': total_jobs_posted,
            'total_jobs_approved': total_jobs_approved,
            'total_jobs_rejected': total_jobs_rejected,
            'total_jobs_pending': total_jobs_pending,
            'total_applications': total_applications,
            'approval_rate': round(
                (total_jobs_approved / total_jobs_posted * 100) 
                if total_jobs_posted > 0 else 0, 1
            ),
            'top_performers': top_performers_data,
            'weekly_activity': {
                'jobs_posted': weekly_jobs,
            }
        })
    
    @action(detail=True, methods=['get'])
    def monthly_breakdown(self, request, pk=None):
        """Get monthly statistics breakdown for a user"""
        stats = self.get_object()
        
        if not request.user.is_staff and stats.user != request.user:
            return Response(
                {'detail': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from apps.jobs.models import Job
        from django.db.models.functions import TruncMonth
        
        # Get monthly job counts
        monthly_jobs = Job.objects.filter(
            created_by=stats.user
        ).annotate(
            month=TruncMonth('posted_at')
        ).values('month').annotate(
            total=Count('id'),
            approved=Count('id', filter=Q(is_approved=True)),
            rejected=Count('id', filter=Q(approval_status='rejected')),
            pending=Count('id', filter=Q(approval_status='pending')),
        ).order_by('-month')[:12]
        
        return Response({
            'user': stats.user.username,
            'monthly_breakdown': list(monthly_jobs)
        })
    
    @action(detail=True, methods=['post'])
    def reset_daily_tracker(self, request, pk=None):
        """Manually reset daily tracker (admin only)"""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        stats = self.get_object()
        stats.reset_daily_tracker()
        return Response({'status': 'daily tracker reset'})