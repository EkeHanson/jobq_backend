from django.db import models
from django.conf import settings


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    price_cents = models.IntegerField()
    max_applications = models.IntegerField(default=0)
    max_profiles = models.IntegerField(default=1)  # Number of profiles user can create
    max_ai_pastes = models.IntegerField(default=0)  # Number of AI job extractions per month
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Subscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    active = models.BooleanField(default=False, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    ai_pastes_used_this_month = models.IntegerField(default=0)
    last_usage_reset = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name if self.plan else 'none'}"

    def get_limits(self):
        """Get the limits for this subscription"""
        if not self.active or not self.plan:
            return {
                'max_applications': 0,
                'max_profiles': 0,
                'max_ai_pastes': 0,
            }
        return {
            'max_applications': self.plan.max_applications,
            'max_profiles': self.plan.max_profiles,
            'max_ai_pastes': self.plan.max_ai_pastes,
        }
