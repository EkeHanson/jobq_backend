from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import SubscriptionPlan, Subscription
from django.utils import timezone
from .serializers import SubscriptionPlanSerializer, SubscriptionSerializer


class SubscriptionViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        # return available plans
        plans = SubscriptionPlan.objects.all()
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def me(self, request):
        sub, _ = Subscription.objects.get_or_create(user=request.user)
        serializer = SubscriptionSerializer(sub)
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


class InvoiceListView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # stub: return empty list
        return Response([])


class InvoiceDownloadView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, invoice_id=None, *args, **kwargs):
        return Response({'url': ''})
