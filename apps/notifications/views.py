from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(user=user)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.read = True
        notif.save()
        return Response(self.get_serializer(notif).data)
