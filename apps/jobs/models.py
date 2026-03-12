from django.db import models
from django.conf import settings
import uuid


class Company(models.Model):
    name = models.CharField(max_length=255)
    website = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Job(models.Model):
    JOB_TYPE_CHOICES = [
        ('Full-time', 'Full-time'),
        ('Part-time', 'Part-time'),
        ('Contract', 'Contract'),
        ('Internship', 'Internship'),
        ('Remote', 'Remote'),
    ]
    
    EXPERIENCE_LEVELS = [
        ('Entry', 'Entry Level'),
        ('Mid-Level', 'Mid-Level'),
        ('Senior', 'Senior'),
        ('Lead', 'Lead'),
        ('Executive', 'Executive'),
    ]
    
    INDUSTRY_CHOICES = [
        ('Technology', 'Technology'),
        ('Healthcare', 'Healthcare'),
        ('Finance', 'Finance'),
        ('Manufacturing', 'Manufacturing'),
        ('Security', 'Security'),
        ('Retail', 'Retail'),
        ('Education', 'Education'),
        ('Construction', 'Construction'),
        ('Transportation', 'Transportation'),
        ('Hospitality', 'Hospitality'),
        ('Media', 'Media'),
        ('Consulting', 'Consulting'),
        ('Legal', 'Legal'),
        ('Real Estate', 'Real Estate'),
        ('Energy', 'Energy'),
        ('Telecommunications', 'Telecommunications'),
        ('Government', 'Government'),
        ('Non-Profit', 'Non-Profit'),
        ('Other', 'Other'),
    ]
    
    title = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    location = models.CharField(max_length=255, blank=True)
    industry = models.CharField(max_length=100, choices=INDUSTRY_CHOICES, default='Other')
    description = models.TextField(blank=True, help_text="Job description (supports HTML formatting)")
    requirements = models.TextField(blank=True, help_text="Job requirements (supports HTML formatting)")
    skills = models.TextField(blank=True, help_text="Required skills (supports HTML formatting)")
    job_type = models.CharField(max_length=50, choices=JOB_TYPE_CHOICES, default='Full-time')
    experience_level = models.CharField(max_length=50, choices=EXPERIENCE_LEVELS, default='Mid-Level')
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    salary_currency = models.CharField(max_length=10, default='USD')
    application_link = models.URLField(blank=True, null=True)
    application_email = models.EmailField(blank=True, null=True)
    posted_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_jobs')

    class Meta:
        ordering = ['-posted_at']  # LIFO - newest first
        indexes = [
            models.Index(fields=['-posted_at']),  # Fast sorting by date
            models.Index(fields=['job_type']),
            models.Index(fields=['experience_level']),
            models.Index(fields=['location']),
            models.Index(fields=['industry']),
        ]

    def __str__(self):
        return f"{self.title} @ {self.company}"


class ExtractionTask(models.Model):
    task_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    input_text = models.TextField()
    status = models.CharField(max_length=20, default='pending')
    result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.task_id)


class JobBookmark(models.Model):
    """Model to store user's bookmarked jobs"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='job_bookmarks')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'job']  # Prevent duplicate bookmarks
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user} bookmarked {self.job}"
