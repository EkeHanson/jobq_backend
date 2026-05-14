from rest_framework import serializers
from .models import Job, Company, ExtractionTask, JobBookmark


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'website', 'description']


class JobSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating jobs (includes approval fields)"""
    company = CompanySerializer()

    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'location', 'industry', 
            'description', 'requirements', 'skills',
            'job_type', 'experience_level', 'salary_min', 'salary_max',
            'salary_currency', 'application_link', 'application_email',
            'is_approved', 'approval_status', 'reviewed_by', 'reviewed_at',
            'rejection_reason', 'is_archived', 'archived_at', 'posted_at', 'created_by',
        ]
        read_only_fields = [
            'is_approved', 'approval_status', 'reviewed_by', 'reviewed_at',
            'is_archived', 'archived_at', 'posted_at', 'created_by',
        ]
    
    def create(self, validated_data):
        company_data = validated_data.pop('company', None)
        if company_data:
            company, _ = Company.objects.get_or_create(**company_data)
            validated_data['company'] = company
        
        # Set default approval status
        user = self.context.get('request').user
        if user and not user.is_staff:
            validated_data['approval_status'] = 'pending'
            validated_data['is_approved'] = False
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        company_data = validated_data.pop('company', None)
        if company_data:
            company, _ = Company.objects.get_or_create(**company_data)
            validated_data['company'] = company
        return super().update(instance, validated_data)


class JobUpdateApprovalSerializer(serializers.ModelSerializer):
    """Serializer for updating job approval status"""
    
    class Meta:
        model = Job
        fields = [
            'id', 'is_approved', 'approval_status', 
            'reviewed_by', 'reviewed_at', 'rejection_reason'
        ]
        read_only_fields = ['id', 'reviewed_at']
    
    def validate(self, data):
        """Validate approval status changes"""
        instance = self.instance
        approval_status = data.get('approval_status')
        is_approved = data.get('is_approved')
        
        if approval_status == 'approved' and not is_approved:
            raise serializers.ValidationError("is_approved must be True when approval_status is 'approved'")
        
        if approval_status == 'rejected' and 'rejection_reason' not in data:
            raise serializers.ValidationError("rejection_reason is required when rejecting a job")
        
        return data
    
    def update(self, instance, validated_data):
        from django.utils import timezone
        
        approval_status = validated_data.get('approval_status')
        is_approved = validated_data.get('is_approved')
        
        # Set reviewed_at to now when status changes
        if approval_status and approval_status != instance.approval_status:
            validated_data['reviewed_at'] = timezone.now()
            validated_data['reviewed_by'] = self.context.get('request').user
        
        return super().update(instance, validated_data)


class ExtractionTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractionTask
        fields = ['task_id', 'input_text', 'status', 'result', 'created_at', 'updated_at']


class JobBookmarkSerializer(serializers.ModelSerializer):
    job = JobSerializer()
    
    class Meta:
        model = JobBookmark
        fields = ['id', 'job', 'created_at']


class BulkJobCreateSerializer(serializers.Serializer):
    jobs = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=100
    )
