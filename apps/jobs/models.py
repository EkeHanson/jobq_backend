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
    title = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    posted_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

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
