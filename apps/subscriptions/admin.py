from django.contrib import admin
from .models import SubscriptionPlan, Subscription

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_cents', 'max_applications', 'max_profiles', 'max_ai_pastes', 'is_active']
    list_filter = ['is_active', 'price_cents']
    search_fields = ['name', 'description']
    ordering = ['price_cents']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'active', 'started_at', 'ai_pastes_used_this_month']
    list_filter = ['active', 'plan']
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ['user']
