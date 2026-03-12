from django.db import models
from django.conf import settings
import uuid


class InterviewPrep(models.Model):
    """Model to store interview preparation data for a user and job"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='interview_preps')
    
    # Link to application (optional - can also be created from job details directly)
    application = models.ForeignKey(
        'applications.Application', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='interview_preps'
    )
    
    # Job information
    job_title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    
    # AI-generated content
    interview_questions = models.JSONField(
        default=list, 
        help_text="List of interview questions with categories"
    )
    skill_assessments = models.JSONField(
        default=dict, 
        help_text="Skill assessments and gaps analysis"
    )
    recommendations = models.JSONField(
        default=list, 
        help_text="Personalized recommendations based on profile"
    )
    company_insights = models.JSONField(
        default=dict, 
        help_text="Information about the company"
    )
    
    # Status
    status = models.CharField(
        max_length=20, 
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ], 
        default='pending'
    )
    
    # Metadata
    prep_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Interview Preparation'
        verbose_name_plural = 'Interview Preparations'

    def __str__(self):
        return f"Interview Prep: {self.job_title} at {self.company_name}"
