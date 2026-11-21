import json
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta


class Role(models.Model):
    ADMIN = 'Admin'
    MANAGER = 'Manager'
    SALES_EXECUTIVE = 'SalesExecutive'
    
    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (MANAGER, 'Manager'),
        (SALES_EXECUTIVE, 'Sales Executive'),
    ]
    
    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.get_name_display() if hasattr(self, 'get_name_display') else self.name


class User(AbstractUser):
    ROLE_ADMIN = 'Admin'
    ROLE_MANAGER = 'Manager'
    ROLE_SALES = 'SalesExecutive'
    
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_MANAGER, 'Manager'),
        (ROLE_SALES, 'Sales Executive'),
    ]
    
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    role_name = models.CharField(max_length=30, choices=ROLE_CHOICES, default=ROLE_SALES)
    phone = models.CharField(max_length=20, blank=True, default='')
    failed_login_count = models.IntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Sync role and role_name
        if self.role and self.role.name != self.role_name:
            self.role_name = self.role.name
        elif not self.role and self.role_name:
            role_obj, _ = Role.objects.get_or_create(name=self.role_name)
            self.role = role_obj
        if self.is_superuser:
            self.role_name = self.ROLE_ADMIN
        super().save(*args, **kwargs)

    @property
    def is_locked(self):
        if self.lockout_until and self.lockout_until > timezone.now():
            return True
        return False

    @property
    def lockout_minutes_remaining(self):
        if self.is_locked:
            delta = self.lockout_until - timezone.now()
            return max(1, int(delta.total_seconds() // 60) + 1)
        return 0

    def record_failed_login(self, max_attempts=5, lockout_minutes=15):
        self.failed_login_count += 1
        if self.failed_login_count >= max_attempts:
            self.lockout_until = timezone.now() + timedelta(minutes=lockout_minutes)
        self.save(update_fields=['failed_login_count', 'lockout_until'])

    def reset_failed_logins(self):
        if self.failed_login_count > 0 or self.lockout_until is not None:
            self.failed_login_count = 0
            self.lockout_until = None
            self.save(update_fields=['failed_login_count', 'lockout_until'])

    def unlock_account(self):
        self.failed_login_count = 0
        self.lockout_until = None
        self.save(update_fields=['failed_login_count', 'lockout_until'])

    @property
    def is_admin_role(self):
        return self.is_superuser or self.role_name == self.ROLE_ADMIN

    @property
    def is_manager_role(self):
        return self.role_name == self.ROLE_MANAGER

    @property
    def is_sales_role(self):
        return self.role_name == self.ROLE_SALES

    def get_role_display_name(self):
        mapping = {
            self.ROLE_ADMIN: 'Admin',
            self.ROLE_MANAGER: 'Manager',
            self.ROLE_SALES: 'Sales Executive',
        }
        return mapping.get(self.role_name, self.role_name or 'User')

    def __str__(self):
        full_name = self.get_full_name()
        return full_name if full_name else self.username


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('LOGIN', 'Login'),
        ('FAILED_LOGIN', 'Failed Login'),
        ('LOGOUT', 'Logout'),
        ('LOCKOUT', 'Account Lockout'),
        ('UNLOCK', 'Account Unlock'),
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('ROLE_CHANGE', 'Role Change'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('LEAD_CONVERSION', 'Lead Conversion'),
        ('STATUS_CHANGE', 'Status Change'),
        ('RESCHEDULE', 'Reschedule Follow-Up'),
        ('SECURITY', 'Security Event'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    user_email = models.CharField(max_length=255, blank=True, default='')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    entity_name = models.CharField(max_length=50, db_index=True)
    record_id = models.CharField(max_length=100, blank=True, default='')
    old_value = models.TextField(blank=True, default='')
    new_value = models.TextField(blank=True, default='')
    result = models.CharField(max_length=30, default='SUCCESS')
    ip_address = models.CharField(max_length=50, blank=True, default='')
    details = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.action} on {self.entity_name} by {self.user_email or 'Anonymous'}"

    @classmethod
    def log(cls, action, entity_name, record_id='', user=None, user_email='', old_value=None, new_value=None, result='SUCCESS', ip_address='', details=''):
        old_val_str = json.dumps(old_value, default=str) if isinstance(old_value, (dict, list)) else (str(old_value) if old_value is not None else '')
        new_val_str = json.dumps(new_value, default=str) if isinstance(new_value, (dict, list)) else (str(new_value) if new_value is not None else '')
        
        email = user_email
        if user and user.is_authenticated and not email:
            email = user.email or user.username

        return cls.objects.create(
            user=user if (user and user.is_authenticated) else None,
            user_email=email,
            action=action,
            entity_name=entity_name,
            record_id=str(record_id),
            old_value=old_val_str,
            new_value=new_val_str,
            result=result,
            ip_address=ip_address,
            details=details,
        )
