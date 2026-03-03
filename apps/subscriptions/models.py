from django.db import models
from django.conf import settings


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    price_cents = models.IntegerField()
    max_applications = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Subscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    active = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name if self.plan else 'none'}"