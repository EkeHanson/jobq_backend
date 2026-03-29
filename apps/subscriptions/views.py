from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count

from .models import SubscriptionPlan, Subscription
from .serializers import SubscriptionPlanSerializer, SubscriptionSerializer
from apps.profiles.models import Profile
from apps.applications.models import Application


# Public view for listing subscription plans (no auth required)
@api_view(['GET'])
@permission_classes([AllowAny])
def public_subscription_plans(request):
    """
    Public endpoint to get available subscription plans
    """
    plans = SubscriptionPlan.objects.filter(is_active=True)
    serializer = SubscriptionPlanSerializer(plans, many=True)
    return Response(serializer.data)


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        if self.action in ['me', 'upgrade', 'cancel', 'resume', 'list_payment_methods', 'add_payment_method', 'invoices', 'download', 'limits']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def list(self, request):
        # return available plans
        plans = SubscriptionPlan.objects.filter(is_active=True)
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def me(self, request):
        sub, _ = Subscription.objects.get_or_create(user=request.user)
        serializer = SubscriptionSerializer(sub)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser], url_path='admin-subscriptions')
    def admin_subscriptions(self, request):
        subscriptions = Subscription.objects.select_related('user', 'plan').all()
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def upgrade(self, request):
        # placeholder logic
        plan_id = request.data.get('plan_id')
        plan = get_object_or_404(SubscriptionPlan, id=plan_id)
        sub, _ = Subscription.objects.get_or_create(user=request.user)
        sub.plan = plan
        sub.active = True
        sub.started_at = timezone.now()
        sub.ai_pastes_used_this_month = 0
        sub.last_usage_reset = timezone.now()
        sub.save()
        return Response(SubscriptionSerializer(sub).data)

    @action(detail=False, methods=['post'])
    def cancel(self, request):
        sub, _ = Subscription.objects.get_or_create(user=request.user)
        sub.active = False
        sub.canceled_at = timezone.now()
        sub.save()
        return Response({'status': 'canceled'})

    @action(detail=False, methods=['post'])
    def resume(self, request):
        sub, _ = Subscription.objects.get_or_create(user=request.user)
        sub.active = True
        sub.canceled_at = None
        sub.save()
        return Response({'status': 'resumed'})

    @action(detail=False, methods=['get'], url_path='payment-methods')
    def list_payment_methods(self, request):
        return Response([])

    @action(detail=False, methods=['post'], url_path='payment-methods')
    def add_payment_method(self, request):
        return Response({'status': 'added'})

    @action(detail=False, methods=['get'])
    def invoices(self, request):
        return Response([])

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        return Response({'url': ''})

    @action(detail=False, methods=['get'])
    def limits(self, request):
        """
        Get current user's subscription limits and usage
        """
        sub, _ = Subscription.objects.get_or_create(user=request.user)
        
        # Get current counts
        profile_count = Profile.objects.filter(user=request.user).count()
        application_count = Application.objects.filter(user=request.user).count()
        
        # Check and reset monthly AI paste usage if needed
        if sub.last_usage_reset:
            days_since_reset = (timezone.now() - sub.last_usage_reset).days
            if days_since_reset >= 30:
                sub.ai_pastes_used_this_month = 0
                sub.last_usage_reset = timezone.now()
                sub.save()
        
        limits = sub.get_limits()
        
        return Response({
            'limits': {
                'max_applications': limits['max_applications'],
                'max_profiles': limits['max_profiles'],
                'max_ai_pastes': limits['max_ai_pastes'],
            },
            'usage': {
                'applications': application_count,
                'profiles': profile_count,
                'ai_pastes_this_month': sub.ai_pastes_used_this_month,
            },
            'subscription': {
                'active': sub.active,
                'plan_name': sub.plan.name if sub.plan else None,
            }
        })

    @action(detail=False, methods=['post'])
    def check_limit(self, request):
        """
        Check if user can perform a specific action based on their subscription
        """
        action_type = request.data.get('action_type')  # 'create_application', 'create_profile', 'use_ai_paste'
        
        sub, _ = Subscription.objects.get_or_create(user=request.user)
        
        if not sub.active or not sub.plan:
            return Response({
                'allowed': False,
                'reason': 'No active subscription',
                'upgrade_required': True,
            })
        
        if action_type == 'create_application':
            current_count = Application.objects.filter(user=request.user).count()
            max_allowed = sub.plan.max_applications

            # 0 means unlimited
            if max_allowed == 0:
                return Response({
                    'allowed': True,
                    'current': current_count,
                    'limit': 0,
                    'reason': None,
                })

            allowed = current_count < max_allowed
            return Response({
                'allowed': allowed,
                'current': current_count,
                'limit': max_allowed,
                'reason': 'Application limit reached' if not allowed else None,
            })
        
        elif action_type == 'create_profile':
            current_count = Profile.objects.filter(user=request.user).count()
            max_allowed = sub.plan.max_profiles

            # 0 means unlimited
            if max_allowed == 0:
                return Response({
                    'allowed': True,
                    'current': current_count,
                    'limit': 0,
                    'reason': None,
                })

            allowed = current_count < max_allowed
            return Response({
                'allowed': allowed,
                'current': current_count,
                'limit': max_allowed,
                'reason': 'Profile limit reached' if not allowed else None,
            })
        
        elif action_type == 'use_ai_paste':
            # Check monthly AI paste usage
            if sub.last_usage_reset:
                days_since_reset = (timezone.now() - sub.last_usage_reset).days
                if days_since_reset >= 30:
                    sub.ai_pastes_used_this_month = 0
                    sub.last_usage_reset = timezone.now()
                    sub.save()
            
            current_count = sub.ai_pastes_used_this_month
            max_allowed = sub.plan.max_ai_pastes
            
            # 0 means unlimited
            if max_allowed == 0:
                return Response({
                    'allowed': True,
                    'current': current_count,
                    'limit': 0,  # 0 means unlimited
                    'reason': None,
                })
            
            allowed = current_count < max_allowed
            return Response({
                'allowed': allowed,
                'current': current_count,
                'limit': max_allowed,
                'reason': 'AI paste limit reached for this month' if not allowed else None,
            })
        
        return Response({'error': 'Invalid action_type'}, status=400)

    @action(detail=False, methods=['post'])
    def record_ai_paste(self, request):
        """
        Record an AI paste usage
        """
        sub, _ = Subscription.objects.get_or_create(user=request.user)
        
        if not sub.active or not sub.plan:
            return Response({'error': 'No active subscription'}, status=403)
        
        # Check if unlimited (0 means unlimited)
        if sub.plan.max_ai_pastes == 0:
            return Response({
                'allowed': True,
                'pastes_used': sub.ai_pastes_used_this_month,
                'pastes_remaining': 0,  # 0 means unlimited
            })
        
        # Check and reset monthly usage if needed
        if sub.last_usage_reset:
            days_since_reset = (timezone.now() - sub.last_usage_reset).days
            if days_since_reset >= 30:
                sub.ai_pastes_used_this_month = 0
                sub.last_usage_reset = timezone.now()
        
        if sub.ai_pastes_used_this_month >= sub.plan.max_ai_pastes:
            return Response({
                'allowed': False,
                'reason': 'AI paste limit reached for this month',
            }, status=403)
        
        sub.ai_pastes_used_this_month += 1
        sub.save()
        
        return Response({
            'allowed': True,
            'pastes_used': sub.ai_pastes_used_this_month,
            'pastes_remaining': sub.plan.max_ai_pastes - sub.ai_pastes_used_this_month,
        })


class InvoiceListView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # stub: return empty list
        return Response([])


class InvoiceDownloadView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, invoice_id=None, *args, **kwargs):
        return Response({'url': ''})
