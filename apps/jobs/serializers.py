from rest_framework import serializers
from .models import Job, Company, ExtractionTask, JobBookmark


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'website', 'description']


class JobSerializer(serializers.ModelSerializer):
    company = CompanySerializer()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'location', 'industry', 'description', 
            'job_type', 'experience_level', 'salary_min', 'salary_max',
            'salary_currency', 'application_link', 'application_email', 'posted_at',
            'is_bookmarked'
        ]

    def get_is_bookmarked(self, obj):
        """Check if the current user has bookmarked this job"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return JobBookmark.objects.filter(user=request.user, job=obj).exists()
        return False

    def validate(self, data):
        """Ensure at least application_link or application_email is provided."""
        if not data.get('application_link') and not data.get('application_email'):
            raise serializers.ValidationError(
                "Either application_link or application_email must be provided."
            )
        return data

    def create(self, validated_data):
        company_data = validated_data.pop('company', None)
        if company_data:
            company, _ = Company.objects.get_or_create(**company_data)
            validated_data['company'] = company
        return super().create(validated_data)

    def update(self, instance, validated_data):
        company_data = validated_data.pop('company', None)
        if company_data:
            company, _ = Company.objects.get_or_create(**company_data)
            instance.company = company
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
