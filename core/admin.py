from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, AuditLog


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role_name', 'is_active', 'failed_login_count', 'lockout_until')
    list_filter = ('role_name', 'is_active', 'is_staff')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('CRM Roles & Security', {
            'fields': ('role', 'role_name', 'phone', 'failed_login_count', 'lockout_until')
        }),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user_email', 'action', 'entity_name', 'record_id', 'result', 'ip_address')
    list_filter = ('action', 'entity_name', 'result', 'timestamp')
    search_fields = ('user_email', 'entity_name', 'record_id', 'details')
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
