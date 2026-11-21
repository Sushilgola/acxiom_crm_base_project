import csv
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from core.models import User, AuditLog
from crm.models import Customer, Lead, Opportunity, FollowUp, Activity
from crm.views import get_scoped_queryset


@login_required
def report_center_view(request):
    return render(request, 'reports/report_center.html')


@login_required
def customer_report_view(request):
    qs = get_scoped_queryset(request.user, Customer.objects.all())

    status_filter = request.GET.get('status', '').strip()
    owner_filter = request.GET.get('owner', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if owner_filter and (request.user.is_admin_role or request.user.is_manager_role):
        qs = qs.filter(assigned_to_id=owner_filter)
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="customers_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Customer Code', 'Name', 'Email', 'Phone', 'Company', 'Status', 'Assigned To', 'Created Date'])
        for c in qs:
            writer.writerow([c.customer_code, c.name, c.email, c.phone, c.company_name, c.status, str(c.assigned_to or ''), c.created_at.strftime('%Y-%m-%d')])
        return response

    sales_users = User.objects.filter(is_active=True)
    return render(request, 'reports/customer_report.html', {
        'customers': qs,
        'status_filter': status_filter,
        'owner_filter': owner_filter,
        'start_date': start_date,
        'end_date': end_date,
        'sales_users': sales_users,
    })


@login_required
def lead_report_view(request):
    qs = get_scoped_queryset(request.user, Lead.objects.all())

    status_filter = request.GET.get('status', '').strip()
    source_filter = request.GET.get('source', '').strip()
    owner_filter = request.GET.get('owner', '').strip()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if source_filter:
        qs = qs.filter(source=source_filter)
    if owner_filter and (request.user.is_admin_role or request.user.is_manager_role):
        qs = qs.filter(assigned_to_id=owner_filter)

    total_leads = qs.count()
    converted_leads = qs.filter(status='Converted').count()
    conv_rate = round((converted_leads / total_leads * 100), 1) if total_leads > 0 else 0

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="leads_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Lead Code', 'Name', 'Company', 'Email', 'Phone', 'Source', 'Status', 'Expected Value', 'Assigned To', 'Created Date'])
        for l in qs:
            writer.writerow([l.lead_code, l.name, l.company_name, l.email, l.phone, l.source, l.status, l.expected_value, str(l.assigned_to or ''), l.created_at.strftime('%Y-%m-%d')])
        return response

    return render(request, 'reports/lead_report.html', {
        'leads': qs,
        'total_leads': total_leads,
        'converted_leads': converted_leads,
        'conv_rate': conv_rate,
        'status_filter': status_filter,
        'source_filter': source_filter,
        'owner_filter': owner_filter,
        'sources': [c[0] for c in Lead.SOURCE_CHOICES],
        'statuses': [c[0] for c in Lead.STATUS_CHOICES],
        'sales_users': User.objects.filter(is_active=True),
    })


@login_required
def followup_report_view(request):
    qs = get_scoped_queryset(request.user, FollowUp.objects.all())
    today = timezone.localdate()

    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        qs = qs.filter(status=status_filter)

    total_followups = qs.count()
    planned_count = qs.filter(status='Planned').count()
    completed_count = qs.filter(status='Completed').count()
    overdue_count = qs.filter(status='Planned', follow_up_date__lt=today).count()
    missed_count = qs.filter(status='Missed').count()

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="followups_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Subject', 'Type', 'Date', 'Status', 'Related To', 'Assigned To', 'Remarks'])
        for f in qs:
            rel = str(f.customer or f.lead or '')
            writer.writerow([f.subject, f.follow_up_type, str(f.follow_up_date), f.status, rel, str(f.assigned_to or ''), f.remarks])
        return response

    return render(request, 'reports/followup_report.html', {
        'followups': qs,
        'total_followups': total_followups,
        'planned_count': planned_count,
        'completed_count': completed_count,
        'overdue_count': overdue_count,
        'missed_count': missed_count,
        'status_filter': status_filter,
    })


@login_required
def opportunity_report_view(request):
    qs = get_scoped_queryset(request.user, Opportunity.objects.all())

    stage_filter = request.GET.get('stage', '').strip()
    if stage_filter:
        qs = qs.filter(stage=stage_filter)

    total_value = qs.aggregate(sum=Sum('amount'))['sum'] or Decimal('0.00')
    weighted_value = sum([o.weighted_amount for o in qs])

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="opportunities_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Opportunity Code', 'Name', 'Customer', 'Amount', 'Stage', 'Probability (%)', 'Weighted Amount', 'Expected Close', 'Status', 'Owner'])
        for o in qs:
            writer.writerow([o.opportunity_code, o.name, o.customer.name, o.amount, o.stage, o.probability, o.weighted_amount, str(o.expected_close_date), o.status, str(o.assigned_to or '')])
        return response

    return render(request, 'reports/opportunity_report.html', {
        'opportunities': qs,
        'total_value': total_value,
        'weighted_value': weighted_value,
        'stage_filter': stage_filter,
        'stages': [c[0] for c in Opportunity.STAGE_CHOICES],
    })


@login_required
def pipeline_report_view(request):
    # Stage-wise and owner-wise pipeline amount (PDF Section 11)
    qs = get_scoped_queryset(request.user, Opportunity.objects.all())

    stage_data = []
    for s_choice in Opportunity.STAGE_CHOICES:
        stg = s_choice[0]
        stg_opps = qs.filter(stage=stg)
        cnt = stg_opps.count()
        tot = stg_opps.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        weighted = sum([o.weighted_amount for o in stg_opps])
        stage_data.append({
            'stage': stg,
            'count': cnt,
            'total': tot,
            'weighted': weighted,
        })

    owner_data = []
    users = User.objects.filter(is_active=True)
    if request.user.is_sales_role:
        users = users.filter(id=request.user.id)

    for u in users:
        u_opps = qs.filter(assigned_to=u)
        if u_opps.exists():
            tot = u_opps.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
            weighted = sum([o.weighted_amount for o in u_opps])
            owner_data.append({
                'user': u,
                'count': u_opps.count(),
                'total': tot,
                'weighted': weighted,
            })

    total_pipeline = qs.filter(status='Open').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    total_weighted = sum([o.weighted_amount for o in qs.filter(status='Open')])

    return render(request, 'reports/pipeline_report.html', {
        'stage_data': stage_data,
        'owner_data': owner_data,
        'total_pipeline': total_pipeline,
        'total_weighted': total_weighted,
    })


@login_required
def conversion_report_view(request):
    # Leads converted vs not converted & Opportunity outcome metrics (PDF Section 11)
    leads_qs = get_scoped_queryset(request.user, Lead.objects.all())
    opps_qs = get_scoped_queryset(request.user, Opportunity.objects.all())

    total_leads = leads_qs.count()
    converted_leads = leads_qs.filter(status='Converted').count()
    lost_leads = leads_qs.filter(status='Lost').count()
    active_leads = leads_qs.exclude(status__in=['Converted', 'Lost']).count()
    lead_conv_rate = round((converted_leads / total_leads * 100), 1) if total_leads > 0 else 0

    total_opps = opps_qs.count()
    won_opps = opps_qs.filter(status='Won').count()
    lost_opps = opps_qs.filter(status='Lost').count()
    open_opps = opps_qs.filter(status='Open').count()
    won_value = opps_qs.filter(status='Won').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    opp_win_rate = round((won_opps / (won_opps + lost_opps) * 100), 1) if (won_opps + lost_opps) > 0 else 0

    return render(request, 'reports/conversion_report.html', {
        'total_leads': total_leads,
        'converted_leads': converted_leads,
        'lost_leads': lost_leads,
        'active_leads': active_leads,
        'lead_conv_rate': lead_conv_rate,
        'total_opps': total_opps,
        'won_opps': won_opps,
        'lost_opps': lost_opps,
        'open_opps': open_opps,
        'won_value': won_value,
        'opp_win_rate': opp_win_rate,
    })


@login_required
def user_activity_report_view(request):
    # User actions and activity counts (PDF Section 11)
    if not (request.user.is_admin_role or request.user.is_manager_role):
        messages.error(request, "Access denied: Requires Manager or Administrator privileges.")
        return redirect('report_center')

    users = User.objects.filter(is_active=True)
    user_stats = []
    for u in users:
        cust_count = Customer.objects.filter(assigned_to=u).count()
        lead_count = Lead.objects.filter(assigned_to=u).count()
        opp_count = Opportunity.objects.filter(assigned_to=u).count()
        follow_count = FollowUp.objects.filter(assigned_to=u).count()
        completed_follow_count = FollowUp.objects.filter(assigned_to=u, status='Completed').count()
        act_count = Activity.objects.filter(assigned_to=u).count()
        audit_count = AuditLog.objects.filter(user=u).count()

        user_stats.append({
            'user': u,
            'customers': cust_count,
            'leads': lead_count,
            'opportunities': opp_count,
            'followups': follow_count,
            'completed_followups': completed_follow_count,
            'activities': act_count,
            'audit_events': audit_count,
        })

    return render(request, 'reports/user_activity_report.html', {'user_stats': user_stats})
