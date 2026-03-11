from rest_framework import serializers
from .models import Notification, ContactMessage, Review


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'link', 'read', 'created_at']


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = [
            'id',
            'name',
            'email',
            'subject',
            'message',
            'created_at',
            'responded',
            'response',
            'responded_at',
            'responded_by',
        ]
        read_only_fields = ['id', 'created_at', 'responded', 'responded_at', 'responded_by']


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user', 'rating', 'title', 'body', 'created_at', 'updated_at', 'published']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
