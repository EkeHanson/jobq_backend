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

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    # Job information - stored directly, no relation to Job model
    job_title = models.CharField(max_length=255, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='saved', db_index=True)
    applied_date = models.DateField(null=True, blank=True, db_index=True)
    deadline = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # New optional fields
    description = models.TextField(blank=True, help_text="Job description from the listing")
    requirements = models.TextField(blank=True, help_text="Job requirements and qualifications")
    resume = models.URLField(max_length=500, blank=True, help_text="Resume URL (uploaded and compressed)")
    recruiter_questions = models.TextField(blank=True, help_text="Questions from the recruiter")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user} -> {self.company_name} - {self.job_title} ({self.status})"


class StatusHistory(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='history')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
