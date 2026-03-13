from django.db import models
from django.conf import settings


class Application(models.Model):
    STATUS_CHOICES = [
        ('saved', 'Saved'),
        ('applied', 'Applied'),
        ('assessment', 'Assessment'),
        ('interview', 'Interview'),
        ('offer', 'Offer'),
        ('rejected', 'Rejected'),
        ('accepted', 'Accepted'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    SOURCE_CHOICES = [
        ('linkedin', 'LinkedIn'),
        ('indeed', 'Indeed'),
        ('company_website', 'Company Website'),
        ('referral', 'Referral'),
        ('recruiter', 'Recruiter'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    # Job information - stored directly, no relation to Job model
    job_title = models.CharField(max_length=255, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='saved', db_index=True)
    applied_date = models.DateField(null=True, blank=True, db_index=True)
    deadline = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Source tracking
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, blank=True, help_text="Where the application came from")
    
    # Follow-up reminders
    follow_up_date = models.DateField(null=True, blank=True, help_text="Date to follow up")
    follow_up_sent = models.BooleanField(default=False, help_text="Whether follow-up reminder was sent")
    
    # New optional fields
    description = models.TextField(blank=True, help_text="Job description from the listing")
    requirements = models.TextField(blank=True, help_text="Job requirements and qualifications")
    resume = models.URLField(max_length=500, blank=True, help_text="Resume URL (uploaded and compressed)")
    recruiter_questions = models.TextField(blank=True, help_text="Questions from the recruiter")
    
    # Archive feature
    archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    # Soft delete
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Soft delete timestamp")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'archived']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['user', 'deleted_at']),
        ]

    def __str__(self):
        return f"{self.user} -> {self.company_name} - {self.job_title} ({self.status})"


class StatusHistory(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='history')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)


class Interview(models.Model):
    """Model to track interview schedules"""
    INTERVIEW_TYPES = [
        ('phone', 'Phone Screen'),
        ('technical', 'Technical'),
        ('hr', 'HR'),
        ('panel', 'Panel'),
        ('final', 'Final'),
        ('other', 'Other'),
    ]
    
    OUTCOME_CHOICES = [
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    interview_date = models.DateTimeField(null=True, blank=True)
    interview_time = models.TimeField(null=True, blank=True)
    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPES, default='phone')
    interviewer = models.CharField(max_length=255, blank=True, help_text="Interviewer name(s)")
    location = models.CharField(max_length=255, blank=True, help_text="Location or meeting link")
    notes = models.TextField(blank=True)
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-interview_date', '-created_at']
    
    def __str__(self):
        return f"Interview for {self.application.job_title} at {self.application.company_name}"
