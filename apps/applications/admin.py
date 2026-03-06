from django.contrib import admin
from .models import Application, StatusHistory

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'job_title', 'company_name', 'status', 'applied_date', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['job_title', 'company_name', 'user__username', 'user__email']
    raw_id_fields = ['user']
    ordering = ['-created_at']

@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'application', 'old_status', 'new_status', 'changed_at']
    list_filter = ['changed_at']
    raw_id_fields = ['application']
    ordering = ['-changed_at']
