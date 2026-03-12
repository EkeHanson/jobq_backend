from rest_framework import serializers
from .models import InterviewPrep


class InterviewPrepSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewPrep
        fields = [
            'id', 'prep_id', 'application', 'job_title', 'company_name',
            'interview_questions', 'skill_assessments', 'recommendations',
            'company_insights', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'prep_id', 'interview_questions', 'skill_assessments',
            'recommendations', 'company_insights', 'status', 'created_at', 'updated_at'
        ]


class InterviewPrepCreateSerializer(serializers.Serializer):
    """Serializer for creating interview prep - accepts job details"""
    application_id = serializers.IntegerField(required=False, allow_null=True)
    job_title = serializers.CharField(max_length=255)
    company_name = serializers.CharField(max_length=255)
    job_description = serializers.CharField(required=False, allow_blank=True)
    job_requirements = serializers.CharField(required=False, allow_blank=True)
    job_skills = serializers.CharField(required=False, allow_blank=True)
