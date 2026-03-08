from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubscriptionViewSet, public_subscription_plans

router = DefaultRouter()
router.register(r'subscription', SubscriptionViewSet, basename='subscription')

urlpatterns = [
    path('', include(router.urls)),
    path('plans/', public_subscription_plans, name='public-subscription-plans'),
]
