from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Subscription, SubscriptionPlan


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_subscription_for_new_user(sender, instance, created, **kwargs):
    """Automatically create an empty subscription for new users"""
    if created:
        # Create an empty subscription - user can select a plan manually in Django admin
        Subscription.objects.create(
            user=instance,
            plan=None,  # No plan assigned - admin must set this
            active=False,  # Not active until a plan is assigned
        )
