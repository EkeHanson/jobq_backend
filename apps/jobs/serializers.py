from rest_framework import serializers
from .models import Job, Company, ExtractionTask


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'website', 'description']


class JobSerializer(serializers.ModelSerializer):
    company = CompanySerializer()

    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'location', 'description', 
            'job_type', 'experience_level', 'salary_min', 'salary_max',
            'salary_currency', 'posted_at'
        ]

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
