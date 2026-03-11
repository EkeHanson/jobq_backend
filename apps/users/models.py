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
