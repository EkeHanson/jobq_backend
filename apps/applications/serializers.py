from rest_framework import serializers
from .models import Application, StatusHistory


class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusHistory
        fields = ['id', 'old_status', 'new_status', 'changed_at', 'notes']


class ApplicationSerializer(serializers.ModelSerializer):
    history = StatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = ['id', 'user', 'job_title', 'company_name', 'status', 'applied_date', 'deadline', 'notes', 'history', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        status = validated_data.get('status')
        if status and status != instance.status:
            StatusHistory.objects.create(
                application=instance,
                old_status=instance.status,
                new_status=status,
            )
        return super().update(instance, validated_data)
