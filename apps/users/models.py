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
    # Job poster status
    is_staff_poster = models.BooleanField(default=False, help_text='Whether user can post jobs (requires approval)')
    assigned_to_staff = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_users', help_text='Staff member this user is assigned to')
    # Job posting limits
    daily_job_limit = models.PositiveIntegerField(default=5, help_text='Maximum jobs that can be posted per day')
    monthly_job_limit = models.PositiveIntegerField(default=50, help_text='Maximum jobs that can be posted per month')
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


class JobPosterStats(models.Model):
    """Statistics tracking for job poster performance"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='poster_stats')
    
    # Overall statistics
    total_jobs_posted = models.PositiveIntegerField(default=0)
    total_jobs_approved = models.PositiveIntegerField(default=0)
    total_jobs_rejected = models.PositiveIntegerField(default=0)
    total_jobs_pending = models.PositiveIntegerField(default=0)
    
    # Approval rate
    average_approval_time = models.DurationField(null=True, blank=True, help_text='Average time from posting to approval')
    
    # Engagement statistics
    total_views = models.PositiveIntegerField(default=0)
    total_applications_received = models.PositiveIntegerField(default=0)
    average_applications_per_job = models.FloatField(default=0.0)
    
    # Daily tracking
    last_post_date = models.DateField(null=True, blank=True)
    jobs_posted_today = models.PositiveIntegerField(default=0)
    
    # Monthly tracking
    current_month = models.DateField(null=True, blank=True, help_text='Current month for tracking (YYYY-MM-01)')
    jobs_posted_this_month = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Job Poster Statistics'
        verbose_name_plural = 'Job Poster Statistics'
        indexes = [
            models.Index(fields=['user', 'current_month']),
            models.Index(fields=['last_post_date']),
        ]
    
    def __str__(self):
        return f'Stats for {self.user.username}'
    
    def update_monthly_tracker(self):
        """Reset monthly tracker if we're in a new month"""
        
        today = timezone.now().date()
        first_of_month = today.replace(day=1)
        
        if self.current_month != first_of_month:
            self.current_month = first_of_month
            self.jobs_posted_this_month = 0
            self.save()
    
    def reset_daily_tracker(self):
        """Reset daily tracker if it's a new day"""
        
        today = timezone.now().date()
        
        if self.last_post_date != today:
            self.last_post_date = today
            self.jobs_posted_today = 0
            self.save()

    def can_post_job(self):
        """Check if user can post more jobs based on limits"""
        self.reset_daily_tracker()
        self.update_monthly_tracker()
        
        if self.jobs_posted_today >= self.user.daily_job_limit:
            return False, f'Daily limit reached ({self.jobs_posted_today}/{self.user.daily_job_limit})'
        
        if self.jobs_posted_this_month >= self.user.monthly_job_limit:
            return False, f'Monthly limit reached ({self.jobs_posted_this_month}/{self.user.monthly_job_limit})'
        
        return True, 'Can post job'

    def increment_job_posted(self):
        """Increment job posted counters"""
        
        today = timezone.now().date()
        
        # Reset trackers if needed
        self.reset_daily_tracker()
        self.update_monthly_tracker()
        
        # Increment counters
        self.total_jobs_posted += 1
        self.total_jobs_pending += 1
        self.jobs_posted_today += 1
        self.jobs_posted_this_month += 1
        self.last_post_date = today
        self.save()

    def job_approved(self):
        """Update stats when a job is approved"""
        self.total_jobs_approved += 1
        self.total_jobs_pending = max(0, self.total_jobs_pending - 1)
        self.save()

    def job_rejected(self):
        """Update stats when a job is rejected"""
        self.total_jobs_rejected += 1
        self.total_jobs_pending = max(0, self.total_jobs_pending - 1)
        self.save()

    def update_application_stats(self, total_applications):
        """Update application statistics"""
        self.total_applications_received = total_applications
        if self.total_jobs_approved > 0:
            self.average_applications_per_job = round(
                total_applications / self.total_jobs_approved, 1
            )
        self.save()

    def update_approval_time(self, approval_duration):
        """Update average approval time"""
        if self.total_jobs_approved > 0:
            total_time = (self.average_approval_time or timedelta(0)) * (self.total_jobs_approved - 1)
            total_time += approval_duration
            self.average_approval_time = total_time / self.total_jobs_approved
        else:
            self.average_approval_time = approval_duration
        self.save()


class JobSearchGoal(models.Model):
    """Weekly job search goal for a user"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='job_search_goal'
    )
    weekly_target = models.PositiveIntegerField(default=10, help_text='Number of applications to submit per week')
    applications_this_week = models.PositiveIntegerField(default=0)
    week_start_date = models.DateField(help_text='Start date of the current week')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Job Search Goal'
        verbose_name_plural = 'Job Search Goals'

    def __str__(self):
        return f'Job Search Goal for {self.user.username}'

    def check_and_reset_week(self):
        """Reset weekly counts if the current week has changed."""
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        if self.week_start_date != week_start:
            self.week_start_date = week_start
            self.applications_this_week = 0
            self.save()

    def get_progress_percentage(self):
        if self.weekly_target <= 0:
            return 0
        return min(100, int((self.applications_this_week / self.weekly_target) * 100))


class StaffAssignment(models.Model):
    """Track which users (job posters) are assigned to which staff members"""
    staff = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='assigned_staff_members',
        limit_choices_to={'is_staff': True},
        help_text='Staff member (job reviewer/approver)'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='staff_assignment',
        help_text='User assigned to this staff member'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, help_text='Whether this assignment is active')
    
    class Meta:
        verbose_name = 'Staff Assignment'
        verbose_name_plural = 'Staff Assignments'
        unique_together = ['staff', 'user']
        indexes = [
            models.Index(fields=['staff', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f'{self.user.username} -> {self.staff.username}'


class JobReviewComment(models.Model):
    """Comments on job posts during the review process"""
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='review_comments')
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reviews_made')
    comment = models.TextField(help_text='Review comment')
    is_internal = models.BooleanField(default=False, help_text='Internal note (not visible to job poster)')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Job Review Comment'
        verbose_name_plural = 'Job Review Comments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Review by {self.reviewer.username if self.reviewer else "System"} on {self.job.title}'


class PasswordResetToken(models.Model):
    """Model to store password reset tokens"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f'Reset token for {self.user.email}'


class TwoFactorToken(models.Model):
    """Model to store two-factor authentication tokens"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='two_factor_tokens')
    token = models.CharField(max_length=6, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = str(secrets.randbelow(1000000)).zfill(6)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f'2FA token for {self.user.email}'


