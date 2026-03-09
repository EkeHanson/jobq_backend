from rest_framework import serializers
from .models import Application, StatusHistory
from .upload_utils import upload_resume, delete_resume


class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusHistory
        fields = ['id', 'old_status', 'new_status', 'changed_at', 'notes']


class ApplicationSerializer(serializers.ModelSerializer):
    history = StatusHistorySerializer(many=True, read_only=True)
    resume_file = serializers.FileField(write_only=True, required=False, help_text="Resume file to upload (will be compressed)")

    class Meta:
        model = Application
        fields = ['id', 'user', 'job_title', 'company_name', 'status', 'applied_date', 'deadline', 'notes', 
                  'description', 'requirements', 'resume', 'recruiter_questions', 'resume_file',
                  'history', 'archived', 'archived_at', 'deleted_at', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at', 'resume', 'archived', 'archived_at', 'deleted_at']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        
        # Handle resume file upload
        resume_file = validated_data.pop('resume_file', None)
        if resume_file:
            try:
                # Determine content type
                content_type = resume_file.content_type if hasattr(resume_file, 'content_type') else 'application/pdf'
                file_name = resume_file.name if hasattr(resume_file, 'name') else 'resume.pdf'
                
                # Upload with compression
                resume_url = upload_resume(resume_file, file_name, content_type)
                validated_data['resume'] = resume_url
                print(f"Resume uploaded successfully: {resume_url}")
            except Exception as e:
                # Log error but continue - don't block application creation
                import logging
                logging.error(f"Failed to upload resume: {str(e)}")
                # Re-raise so we can see the error
                raise serializers.ValidationError({'resume_file': f'Failed to upload resume: {str(e)}'})
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        status = validated_data.get('status')
        if status and status != instance.status:
            StatusHistory.objects.create(
                application=instance,
                old_status=instance.status,
                new_status=status,
            )
        
        # Handle resume file upload
        resume_file = validated_data.pop('resume_file', None)
        if resume_file:
            try:
                # Delete old resume if exists
                if instance.resume:
                    delete_resume(instance.resume)
                
                # Determine content type
                content_type = resume_file.content_type if hasattr(resume_file, 'content_type') else 'application/pdf'
                file_name = resume_file.name if hasattr(resume_file, 'name') else 'resume.pdf'
                
                # Upload with compression
                resume_url = upload_resume(resume_file, file_name, content_type)
                validated_data['resume'] = resume_url
            except Exception as e:
                # Log error but continue - don't block application update
                import logging
                logging.error(f"Failed to upload resume: {str(e)}")
        
        return super().update(instance, validated_data)
