from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from .models import User, Role, AuditLog
from .forms import (
    LoginForm, RegisterForm, AdminUserCreateForm, AdminUserEditForm, AdminPasswordResetForm
)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        ip = get_client_ip(request)
        username = request.POST.get('username', '').strip()
        
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            AuditLog.log(
                action='LOGIN',
                entity_name='Auth',
                record_id=str(user.id),
                user=user,
                user_email=user.email or user.username,
                result='SUCCESS',
                ip_address=ip,
                details=f"User {user.username} successfully logged in."
            )
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            next_url = request.GET.get('next')
            return redirect(next_url if next_url else 'dashboard')
        else:
            AuditLog.log(
                action='FAILED_LOGIN',
                entity_name='Auth',
                user_email=username,
                result='FAILURE',
                ip_address=ip,
                details=f"Failed login attempt for username/email '{username}'."
            )
    else:
        form = LoginForm()

    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        user = request.user
        AuditLog.log(
            action='LOGOUT',
            entity_name='Auth',
            record_id=str(user.id),
            user=user,
            user_email=user.email or user.username,
            result='SUCCESS',
            ip_address=get_client_ip(request),
            details=f"User {user.username} logged out."
        )
        logout(request)
        messages.info(request, "You have been logged out successfully.")
    return redirect('login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            ip = get_client_ip(request)
            AuditLog.log(
                action='CREATE',
                entity_name='User',
                record_id=str(user.id),
                user=user,
                user_email=user.email,
                result='SUCCESS',
                ip_address=ip,
                details=f"New user self-registered: {user.username} (Role: {user.role_name})."
            )
            login(request, user)
            messages.success(request, "Registration successful! Welcome to AcxiomCRM.")
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'core/register.html', {'form': form})


@login_required
def user_list_view(request):
    # Only Admin allowed for full user management
    if not request.user.is_admin_role:
        messages.error(request, "Access denied: User management requires Administrator privileges.")
        return redirect('dashboard')

    users = User.objects.all().order_by('-date_joined')
    search_query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    if role_filter:
        users = users.filter(role_name=role_filter)

    if status_filter:
        if status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)
        elif status_filter == 'locked':
            users = [u for u in users if u.is_locked]

    paginator = Paginator(users, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    roles = Role.objects.all()

    return render(request, 'core/user_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': roles,
    })


@login_required
def user_create_view(request):
    if not request.user.is_admin_role:
        messages.error(request, "Access denied: Administrator privileges required.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            AuditLog.log(
                action='CREATE',
                entity_name='User',
                record_id=str(new_user.id),
                user=request.user,
                new_value={'username': new_user.username, 'email': new_user.email, 'role': new_user.role_name},
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Administrator {request.user.username} created user {new_user.username} with role {new_user.role_name}."
            )
            messages.success(request, f"User {new_user.username} created successfully.")
            return redirect('user_list')
    else:
        form = AdminUserCreateForm()

    return render(request, 'core/user_form.html', {'form': form, 'title': 'Create New User'})


@login_required
def user_edit_view(request, user_id):
    if not request.user.is_admin_role:
        messages.error(request, "Access denied: Administrator privileges required.")
        return redirect('dashboard')

    target_user = get_object_or_404(User, id=user_id)
    old_data = {
        'username': target_user.username,
        'email': target_user.email,
        'role': target_user.role_name,
        'is_active': target_user.is_active,
        'is_locked': target_user.is_locked,
    }

    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            updated_user = form.save()
            new_data = {
                'username': updated_user.username,
                'email': updated_user.email,
                'role': updated_user.role_name,
                'is_active': updated_user.is_active,
                'is_locked': updated_user.is_locked,
            }
            action_type = 'ROLE_CHANGE' if old_data['role'] != new_data['role'] else 'UPDATE'
            AuditLog.log(
                action=action_type,
                entity_name='User',
                record_id=str(updated_user.id),
                user=request.user,
                old_value=old_data,
                new_value=new_data,
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"User {updated_user.username} updated by admin {request.user.username}."
            )
            messages.success(request, f"User {updated_user.username} updated successfully.")
            return redirect('user_list')
    else:
        form = AdminUserEditForm(instance=target_user)

    return render(request, 'core/user_form.html', {'form': form, 'title': f"Edit User: {target_user.username}", 'target_user': target_user})


@login_required
def user_toggle_status_view(request, user_id):
    if not request.user.is_admin_role:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('user_list')

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=['is_active'])

    AuditLog.log(
        action='UPDATE',
        entity_name='User',
        record_id=str(target_user.id),
        user=request.user,
        result='SUCCESS',
        ip_address=get_client_ip(request),
        details=f"User {target_user.username} {'activated' if target_user.is_active else 'deactivated'} by {request.user.username}."
    )
    messages.success(request, f"User {target_user.username} is now {'Active' if target_user.is_active else 'Inactive'}.")
    return redirect('user_list')


@login_required
def user_unlock_view(request, user_id):
    if not request.user.is_admin_role:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    target_user = get_object_or_404(User, id=user_id)
    target_user.unlock_account()

    AuditLog.log(
        action='UNLOCK',
        entity_name='User',
        record_id=str(target_user.id),
        user=request.user,
        result='SUCCESS',
        ip_address=get_client_ip(request),
        details=f"Account lockout cleared for {target_user.username} by admin {request.user.username}."
    )
    messages.success(request, f"Account for {target_user.username} has been unlocked.")
    return redirect('user_list')


@login_required
def user_reset_password_view(request, user_id):
    if not request.user.is_admin_role:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    target_user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = AdminPasswordResetForm(request.POST)
        if form.is_valid():
            new_pass = form.cleaned_data['new_password']
            target_user.set_password(new_pass)
            target_user.unlock_account()
            target_user.save()

            AuditLog.log(
                action='PASSWORD_CHANGE',
                entity_name='User',
                record_id=str(target_user.id),
                user=request.user,
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Password for user {target_user.username} reset by admin {request.user.username}."
            )
            messages.success(request, f"Password for {target_user.username} reset successfully.")
            return redirect('user_list')
    else:
        form = AdminPasswordResetForm()

    return render(request, 'core/user_password_reset.html', {'form': form, 'target_user': target_user})


@login_required
def audit_log_list_view(request):
    # Only Admin and Manager (with limited or full view) can view audit logs
    if request.user.is_sales_role:
        messages.error(request, "Access denied: Sales Executives do not have permission to view audit logs.")
        return redirect('dashboard')

    logs = AuditLog.objects.all().order_by('-timestamp')

    action_filter = request.GET.get('action', '').strip()
    entity_filter = request.GET.get('entity', '').strip()
    user_filter = request.GET.get('user', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    if action_filter:
        logs = logs.filter(action=action_filter)
    if entity_filter:
        logs = logs.filter(entity_name__iexact=entity_filter)
    if user_filter:
        logs = logs.filter(Q(user_email__icontains=user_filter) | Q(user__username__icontains=user_filter))
    if start_date:
        logs = logs.filter(timestamp__date__gte=start_date)
    if end_date:
        logs = logs.filter(timestamp__date__lte=end_date)

    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    actions = [c[0] for c in AuditLog.ACTION_CHOICES]
    entities = ['Customer', 'Lead', 'Opportunity', 'FollowUp', 'Activity', 'User', 'Auth']

    return render(request, 'core/audit_log.html', {
        'page_obj': page_obj,
        'action_filter': action_filter,
        'entity_filter': entity_filter,
        'user_filter': user_filter,
        'start_date': start_date,
        'end_date': end_date,
        'actions': actions,
        'entities': entities,
    })
