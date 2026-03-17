from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Notification, ContactMessage, Review
from .serializers import NotificationSerializer, ContactMessageSerializer, ReviewSerializer


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


class ContactMessageViewSet(viewsets.ModelViewSet):
    queryset = ContactMessage.objects.all().order_by('-created_at')
    serializer_class = ContactMessageSerializer

    def get_permissions(self):
        # Any user can create a contact message, but only staff can list/update.
        if self.action in ['create']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def perform_create(self, serializer):
        serializer.save()


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().order_by('-created_at')
    serializer_class = ReviewSerializer

    def get_permissions(self):
        # Anyone can view published reviews, but only authenticated users can create.
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        # Only show published reviews to non-admins, but show own unpublished reviews
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            # Show published reviews OR user's own unpublished reviews
            qs = qs.filter(
                Q(published=True) | Q(user=self.request.user)
            )
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
