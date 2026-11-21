from django.utils import timezone
from .models import FollowUp


def crm_global_context(request):
    if not request.user.is_authenticated:
        return {
            'app_name': 'AcxiomCRM',
            'pending_followups_count': 0,
            'overdue_followups_count': 0,
        }

    today = timezone.localdate()
    user = request.user

    # Follow-up scope based on role
    followups = FollowUp.objects.filter(status='Planned')
    if not (user.is_admin_role or user.is_manager_role):
        followups = followups.filter(assigned_to=user)

    overdue_count = followups.filter(follow_up_date__lt=today).count()
    today_count = followups.filter(follow_up_date=today).count()

    return {
        'app_name': 'AcxiomCRM',
        'pending_followups_count': today_count,
        'overdue_followups_count': overdue_count,
        'current_user_role': user.get_role_display_name(),
    }
