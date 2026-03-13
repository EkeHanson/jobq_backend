from django.contrib.auth.models import AbstractUser
from django.db import models
import secrets
from datetime import timedelta
from django.utils import timezone


class User(AbstractUser):
    # extend user in future
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    # Make email unique at database level
    email = models.EmailField(unique=True)
    # Suspension status
    is_suspended = models.BooleanField(default=False, help_text='Whether the user account is suspended')
    suspension_reason = models.TextField(blank=True, help_text='Reason for suspension')
    suspended_at = models.DateTimeField(null=True, blank=True, help_text='When the user was suspended')
    # Two-Factor Authentication
    is_2fa_enabled = models.BooleanField(default=False, help_text='Whether 2FA is enabled for this account')
    # Notification settings
    email_notifications = models.BooleanField(default=True, help_text='Receive email notifications')
    push_notifications = models.BooleanField(default=True, help_text='Receive push notifications')
    weekly_summary = models.BooleanField(default=True, help_text='Receive weekly summary emails')
    # Privacy settings
    allow_data_collection = models.BooleanField(default=True, help_text='Allow analytics data collection')


class PublicProfile(models.Model):
    """Model for public job search progress sharing"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='public_profile')
    public_slug = models.CharField(max_length=50, unique=True, help_text='Custom URL slug for sharing')
    is_public = models.BooleanField(default=False, help_text='Whether profile is publicly visible')
    show_applications_count = models.BooleanField(default=True, help_text='Show total applications count')
    show_interviews_count = models.BooleanField(default=True, help_text='Show interviews count')
    show_offers_count = models.BooleanField(default=True, help_text='Show offers count')
    show_success_rate = models.BooleanField(default=True, help_text='Show success rate')
    display_name = models.CharField(max_length=100, blank=True, help_text='Custom display name')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Public Profile: {self.public_slug}"
    
    def save(self, *args, **kwargs):
        if not self.public_slug:
            # Generate unique slug
            self.public_slug = secrets.token_urlsafe(8)[:10]
        super().save(*args, **kwargs)
    
    def get_stats(self):
        """Get public statistics for display"""
        from apps.applications.models import Application
        
        apps = Application.objects.filter(user=self.user, archived=False, deleted_at__isnull=True)
        total = apps.count()
        interviews = apps.filter(status='interview').count()
        offers = apps.filter(status='offer').count()
        accepted = apps.filter(status='accepted').count()
        
        success_rate = (accepted / total * 100) if total > 0 else 0
        interview_rate = (interviews / total * 100) if total > 0 else 0
        
        return {
            'total_applications': total,
            'interviews': interviews,
            'offers': offers,
            'accepted': accepted,
            'success_rate': round(success_rate, 1),
            'interview_rate': round(interview_rate, 1),
        }


class JobSearchGoal(models.Model):
    """Model to track user's job search weekly goals"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='job_search_goal')
    weekly_target = models.PositiveIntegerField(default=10, help_text="Number of applications to submit per week")
    applications_this_week = models.PositiveIntegerField(default=0)
    week_start_date = models.DateField(help_text="Start date of the current week")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Goal for {self.user.username}: {self.applications_this_week}/{self.weekly_target}"

    def check_and_reset_week(self):
        """Check if it's a new week and reset the counter if needed"""
        today = timezone.now().date()
        # Calculate the start of the week (Monday)
        week_start = today - timedelta(days=today.weekday())
        
        if self.week_start_date < week_start:
            # New week, reset counter
            self.applications_this_week = 0
            self.week_start_date = week_start
            self.save()

    def increment_applications(self):
        """Increment the application count for this week"""
        self.check_and_reset_week()
        self.applications_this_week += 1
        self.save()

    def get_progress_percentage(self):
        """Get the progress percentage"""
        if self.weekly_target == 0:
            return 0
        return min(100, (self.applications_this_week / self.weekly_target) * 100)


class TwoFactorToken(models.Model):
    """Model to store 2FA verification tokens"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='two_factor_tokens')
    token = models.CharField(max_length=6, db_index=True)  # 6-digit code
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            # Generate a 6-digit token
            self.token = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        if not self.expires_at:
            # Default expiry is 10 minutes
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Check if token is still valid (not expired and not used)"""
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"2FA token for {self.user.email}"


class PasswordResetToken(models.Model):
    """Model to store password reset tokens"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            # Generate a unique token if not provided
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            # Default expiry is 1 hour
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Check if token is still valid (not expired and not used)"""
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"Reset token for {self.user.email}"
