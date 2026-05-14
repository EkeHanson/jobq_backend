from rest_framework import serializers
from .models import StaffAssignment, JobPosterStats
from django.contrib.auth import get_user_model

User = get_user_model()


class UserStaffSerializer(serializers.ModelSerializer):
    """Simplified user serializer for staff assignment"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff']


class StaffAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for staff assignments"""
    staff = UserStaffSerializer(read_only=True)
    staff_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_staff=True),
        source='staff',
        write_only=True
    )
    user = UserStaffSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='user',
        write_only=True
    )
    
    class Meta:
        model = StaffAssignment
        fields = [
            'id', 'staff', 'staff_id', 'user', 'user_id',
            'assigned_at', 'is_active'
        ]
        read_only_fields = ['assigned_at']
    
    def validate(self, data):
        """Validate that user is not already assigned to another staff member"""
        staff = data.get('staff')
        user = data.get('user')
        
        if staff and user:
            # Check for active assignment to different staff
            existing = StaffAssignment.objects.filter(
                user=user,
                is_active=True
            ).exclude(staff=staff)
            
            if existing.exists():
                raise serializers.ValidationError(
                    {'user': 'This user is already assigned to another staff member'}
                )
        
        return data


class StaffAssignmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating staff assignments with user details"""
    
    class Meta:
        model = StaffAssignment
        fields = ['id', 'staff_id', 'user_id', 'is_active']
    
    def to_representation(self, instance):
        """Use full serializer for read operations"""
        return StaffAssignmentSerializer(instance, context=self.context).data


class JobPosterStatsSerializer(serializers.ModelSerializer):
    """Serializer for job poster statistics"""
    user = UserStaffSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='user',
        write_only=True
    )
    approval_rate = serializers.SerializerMethodField()
    days_until_limit = serializers.SerializerMethodField()
    can_post_today = serializers.SerializerMethodField()
    can_post_monthly = serializers.SerializerMethodField()
    daily_job_limit = serializers.SerializerMethodField()
    monthly_job_limit = serializers.SerializerMethodField()
    
    class Meta:
        model = JobPosterStats
        fields = [
            'id', 'user', 'user_id',
            'total_jobs_posted', 'total_jobs_approved', 'total_jobs_rejected', 'total_jobs_pending',
            'approval_rate',
            'average_approval_time',
            'total_views', 'total_applications_received', 'average_applications_per_job',
            'daily_job_limit', 'monthly_job_limit',
            'jobs_posted_today', 'jobs_posted_this_month',
            'can_post_today', 'can_post_monthly', 'days_until_limit',
            'last_post_date', 'current_month',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'total_jobs_posted', 'total_jobs_approved', 'total_jobs_rejected', 'total_jobs_pending',
            'average_approval_time', 'total_views', 'total_applications_received',
            'average_applications_per_job', 'jobs_posted_today', 'jobs_posted_this_month',
            'last_post_date', 'current_month'
        ]
    
    def get_approval_rate(self, obj):
        """Calculate approval rate percentage"""
        if obj.total_jobs_posted > 0:
            return round((obj.total_jobs_approved / obj.total_jobs_posted) * 100, 1)
        return 0.0
    
    def get_can_post_today(self, obj):
        """Check if user can post jobs today"""
        can_post, _ = obj.can_post_job()
        return can_post
    
    def get_can_post_monthly(self, obj):
        """Check if user can post jobs this month"""
        can_post, message = obj.can_post_job()
        # Check specifically monthly limit
        if obj.jobs_posted_this_month >= obj.user.monthly_job_limit:
            return False
        return True
    
    def get_days_until_limit(self, obj):
        """Calculate days until monthly limit reset"""
        from django.utils import timezone
        from calendar import monthrange
        
        today = timezone.now().date()
        _, days_in_month = monthrange(today.year, today.month)
        days_until_reset = days_in_month - today.day
        
        return days_until_reset
    
    def get_daily_job_limit(self, obj):
        """Get user's daily job limit"""
        return obj.user.daily_job_limit
    
    def get_monthly_job_limit(self, obj):
        """Get user's monthly job limit"""
        return obj.user.monthly_job_limit


class UserStaffAssignmentSerializer(serializers.ModelSerializer):
    """Serializer showing user with their staff assignment"""
    assigned_to = UserStaffSerializer(source='assigned_to_staff', read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_staff=True),
        source='assigned_to_staff',
        write_only=True,
        allow_null=True,
        required=False
    )
    is_staff_poster = serializers.BooleanField()
    daily_job_limit = serializers.IntegerField()
    monthly_job_limit = serializers.IntegerField()
    stats = JobPosterStatsSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_staff_poster', 'assigned_to', 'assigned_to_id',
            'daily_job_limit', 'monthly_job_limit',
            'is_suspended', 'is_staff',
            'stats'
        ]
        read_only_fields = ['username', 'email', 'is_staff']