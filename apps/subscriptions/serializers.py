from rest_framework import serializers
from .models import SubscriptionPlan, Subscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'price_cents', 'max_applications', 'max_profiles', 'max_ai_pastes', 'description', 'is_active']


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer()

    class Meta:
        model = Subscription
        fields = ['id', 'plan', 'active', 'started_at', 'canceled_at', 'ai_pastes_used_this_month', 'last_usage_reset']
