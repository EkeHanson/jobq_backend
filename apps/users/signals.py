from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.applications.models import Application


@receiver(post_save, sender=Application)
def increment_job_search_goal(sender, instance, created, **kwargs):
    """
    Automatically increment the job search goal when a new application is created.
    """
    if created:
        try:
            from .models import JobSearchGoal
            goal = JobSearchGoal.objects.filter(user=instance.user).first()
            if goal:
                goal.increment_applications()
        except Exception:
            # Silently fail if goal doesn't exist or other error
            pass
