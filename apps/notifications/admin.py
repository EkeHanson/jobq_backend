from django.contrib import admin
from .models import Notification, ContactMessage


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'read', 'created_at')
    list_filter = ('read',)
    search_fields = ('message',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at', 'responded')
    list_filter = ('responded',)
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)
