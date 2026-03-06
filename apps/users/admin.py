from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import PasswordResetToken

User = get_user_model()

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']

admin.site.register(PasswordResetToken)
