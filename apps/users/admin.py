from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import PasswordResetToken, TwoFactorToken

User = get_user_model()

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_suspended', 'is_2fa_enabled', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'is_suspended', 'is_2fa_enabled', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone', 'location')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Suspension', {'fields': ('is_suspended', 'suspension_reason', 'suspended_at')}),
        ('Two-Factor Authentication', {'fields': ('is_2fa_enabled',)}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ['last_login', 'date_joined', 'suspended_at']
    
    actions = ['suspend_users', 'unsuspend_users']
    
    def suspend_users(self, request, queryset):
        for user in queryset:
            user.is_suspended = True
            user.suspension_reason = 'Suspended by admin'
            user.suspended_at = timezone.now()
            user.save()
        self.message_user(request, f'{queryset.count()} user(s) have been suspended.')
    suspend_users.short_description = 'Suspend selected users'
    
    def unsuspend_users(self, request, queryset):
        for user in queryset:
            user.is_suspended = False
            user.suspension_reason = ''
            user.suspended_at = None
            user.save()
        self.message_user(request, f'{queryset.count()} user(s) have been unsuspended.')
    unsuspend_users.short_description = 'Unsuspend selected users'

admin.site.register(PasswordResetToken)
admin.site.register(TwoFactorToken)
