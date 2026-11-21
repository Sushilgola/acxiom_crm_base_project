import json
from decimal import Decimal
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.http import JsonResponse, HttpResponseForbidden
from core.models import User, AuditLog
from core.views import get_client_ip
from .models import Customer, Lead, Opportunity, FollowUp, Activity
from .forms import (
    CustomerForm, LeadForm, OpportunityForm, FollowUpForm,
    FollowUpRescheduleForm, ActivityForm, LeadConversionForm
)


# Helper: Check role permissions for record scoping
def get_scoped_queryset(user, queryset, user_field='assigned_to'):
    if user.is_admin_role or user.is_manager_role:
        return queryset
    # Sales Executive sees only assigned records
    return queryset.filter(**{user_field: user})


def can_manage_record(user, record, user_field='assigned_to'):
    if user.is_admin_role or user.is_manager_role:
        return True
    assigned_user = getattr(record, user_field, None)
    return assigned_user == user


# ==========================================
# DASHBOARD
# ==========================================
@login_required
def dashboard_view(request):
    user = request.user
    today = timezone.localdate()

    # Scope querysets
    customers = get_scoped_queryset(user, Customer.objects.all())
    leads = get_scoped_queryset(user, Lead.objects.all())
    opportunities = get_scoped_queryset(user, Opportunity.objects.all())
    followups = get_scoped_queryset(user, FollowUp.objects.all())
    activities = get_scoped_queryset(user, Activity.objects.all())

    # Date range filter for dashboard
    date_range = request.GET.get('date_range', 'all')
    if date_range == 'today':
        leads = leads.filter(created_at__date=today)
        opportunities = opportunities.filter(created_at__date=today)
    elif date_range == 'week':
        week_start = today - timedelta(days=today.weekday())
        leads = leads.filter(created_at__date__gte=week_start)
        opportunities = opportunities.filter(created_at__date__gte=week_start)
    elif date_range == 'month':
        leads = leads.filter(created_at__year=today.year, created_at__month=today.month)
        opportunities = opportunities.filter(created_at__year=today.year, created_at__month=today.month)

    # Required KPI Cards (PDF Section 17.11)
    total_customers = customers.count()
    total_leads = leads.count()
    open_leads = leads.exclude(status__in=['Converted', 'Lost']).count()
    total_opportunities = opportunities.count()
    open_opportunities = opportunities.filter(status='Open').count()
    won_opportunities = opportunities.filter(status='Won').count()
    lost_opportunities = opportunities.filter(status='Lost').count()

    total_pipeline_val = opportunities.filter(status='Open').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Chart 1: Lead Status breakdown
    lead_status_counts = {
        'New': leads.filter(status='New').count(),
        'Contacted': leads.filter(status='Contacted').count(),
        'Qualified': leads.filter(status='Qualified').count(),
        'Unqualified': leads.filter(status='Unqualified').count(),
        'Converted': leads.filter(status='Converted').count(),
        'Lost': leads.filter(status='Lost').count(),
    }

    # Chart 2: Opportunity Pipeline Stage Breakdown
    stage_counts = {
        'Qualification': opportunities.filter(stage='Qualification').count(),
        'Proposal': opportunities.filter(stage='Proposal').count(),
        'Negotiation': opportunities.filter(stage='Negotiation').count(),
        'Won': opportunities.filter(stage='Won').count(),
        'Lost': opportunities.filter(stage='Lost').count(),
    }

    # Chart 3: Monthly Sales (Won deals over last 6 months)
    monthly_sales = []
    month_labels = []
    for i in range(5, -1, -1):
        target_month_date = today.replace(day=1) - timedelta(days=i * 30)
        m_name = target_month_date.strftime('%b %Y')
        month_labels.append(m_name)
        val = opportunities.filter(
            status='Won',
            created_at__year=target_month_date.year,
            created_at__month=target_month_date.month
        ).aggregate(sum=Sum('amount'))['sum'] or Decimal('0.00')
        monthly_sales.append(float(val))

    # Overdue and Upcoming Follow-ups
    pending_followups = followups.filter(status='Planned')
    overdue_followups = pending_followups.filter(follow_up_date__lt=today).order_by('follow_up_date')[:5]
    today_followups = pending_followups.filter(follow_up_date=today).order_by('follow_up_time')[:5]
    recent_activities = activities.order_by('-activity_date')[:6]

    context = {
        'total_customers': total_customers,
        'total_leads': total_leads,
        'open_leads': open_leads,
        'total_opportunities': total_opportunities,
        'open_opportunities': open_opportunities,
        'won_opportunities': won_opportunities,
        'lost_opportunities': lost_opportunities,
        'total_pipeline_val': total_pipeline_val,
        'date_range': date_range,
        'lead_status_labels': json.dumps(list(lead_status_counts.keys())),
        'lead_status_data': json.dumps(list(lead_status_counts.values())),
        'stage_labels': json.dumps(list(stage_counts.keys())),
        'stage_data': json.dumps(list(stage_counts.values())),
        'month_labels': json.dumps(month_labels),
        'monthly_sales': json.dumps(monthly_sales),
        'overdue_followups': overdue_followups,
        'today_followups': today_followups,
        'recent_activities': recent_activities,
    }
    return render(request, 'crm/dashboard.html', context)


# ==========================================
# CUSTOMER MANAGEMENT
# ==========================================
@login_required
def customer_list_view(request):
    qs = get_scoped_queryset(request.user, Customer.objects.all())

    # Search & filters (PDF Section 17.13: Customer Name, Email, Phone, Company)
    search_q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    owner_filter = request.GET.get('owner', '').strip()

    if search_q:
        qs = qs.filter(
            Q(name__icontains=search_q) |
            Q(email__icontains=search_q) |
            Q(phone__icontains=search_q) |
            Q(company_name__icontains=search_q) |
            Q(customer_code__icontains=search_q)
        )

    if status_filter:
        qs = qs.filter(status=status_filter)

    if owner_filter and (request.user.is_admin_role or request.user.is_manager_role):
        qs = qs.filter(assigned_to_id=owner_filter)

    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    sales_users = User.objects.filter(is_active=True)

    return render(request, 'crm/customer_list.html', {
        'page_obj': page_obj,
        'search_q': search_q,
        'status_filter': status_filter,
        'owner_filter': owner_filter,
        'sales_users': sales_users,
    })


@login_required
def customer_detail_view(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    if not can_manage_record(request.user, customer):
        messages.error(request, "Access denied: You can only view customers assigned to you.")
        return redirect('customer_list')

    opportunities = customer.opportunities.all()
    followups = customer.followups.all()
    activities = customer.activities.all()
    audit_logs = AuditLog.objects.filter(entity_name='Customer', record_id=str(customer.id))

    return render(request, 'crm/customer_detail.html', {
        'customer': customer,
        'opportunities': opportunities,
        'followups': followups,
        'activities': activities,
        'audit_logs': audit_logs,
    })


@login_required
def customer_create_view(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST, user=request.user)
        if form.is_valid():
            customer = form.save(commit=False)
            if not customer.assigned_to:
                customer.assigned_to = request.user
            customer.save()

            AuditLog.log(
                action='CREATE',
                entity_name='Customer',
                record_id=str(customer.id),
                user=request.user,
                new_value={
                    'name': customer.name,
                    'code': customer.customer_code,
                    'email': customer.email,
                    'phone': customer.phone,
                    'company': customer.company_name,
                    'status': customer.status,
                    'assigned_to': str(customer.assigned_to),
                },
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Customer '{customer.name}' created by {request.user.username}."
            )
            messages.success(request, f"Customer '{customer.name}' created successfully ({customer.customer_code}).")
            return redirect('customer_detail', customer_id=customer.id)
    else:
        form = CustomerForm(user=request.user)

    return render(request, 'crm/customer_form.html', {'form': form, 'title': 'Create New Customer'})


@login_required
def customer_edit_view(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    if not can_manage_record(request.user, customer):
        messages.error(request, "Access denied: You do not have permission to modify this customer.")
        return redirect('customer_list')

    old_data = {
        'name': customer.name,
        'email': customer.email,
        'phone': customer.phone,
        'company': customer.company_name,
        'status': customer.status,
        'assigned_to': str(customer.assigned_to),
    }

    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer, user=request.user)
        if form.is_valid():
            updated_customer = form.save()
            new_data = {
                'name': updated_customer.name,
                'email': updated_customer.email,
                'phone': updated_customer.phone,
                'company': updated_customer.company_name,
                'status': updated_customer.status,
                'assigned_to': str(updated_customer.assigned_to),
            }
            action_type = 'STATUS_CHANGE' if old_data['status'] != new_data['status'] else 'UPDATE'
            AuditLog.log(
                action=action_type,
                entity_name='Customer',
                record_id=str(updated_customer.id),
                user=request.user,
                old_value=old_data,
                new_value=new_data,
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Customer '{updated_customer.name}' updated by {request.user.username}."
            )
            messages.success(request, f"Customer '{updated_customer.name}' updated successfully.")
            return redirect('customer_detail', customer_id=updated_customer.id)
    else:
        form = CustomerForm(instance=customer, user=request.user)

    return render(request, 'crm/customer_form.html', {'form': form, 'title': f"Edit Customer: {customer.name}", 'customer': customer})


@login_required
def customer_delete_view(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    if not can_manage_record(request.user, customer):
        messages.error(request, "Access denied.")
        return redirect('customer_list')

    if request.method == 'POST':
        c_name = customer.name
        c_id = customer.id
        # Log deletion before actual delete
        AuditLog.log(
            action='DELETE',
            entity_name='Customer',
            record_id=str(c_id),
            user=request.user,
            old_value={'name': c_name, 'code': customer.customer_code, 'email': customer.email},
            result='SUCCESS',
            ip_address=get_client_ip(request),
            details=f"Customer '{c_name}' deleted by {request.user.username}."
        )
        customer.delete()
        messages.success(request, f"Customer '{c_name}' was deleted.")
        return redirect('customer_list')

    return render(request, 'crm/confirm_delete.html', {
        'object_name': f"Customer: {customer.name} ({customer.customer_code})",
        'cancel_url': 'customer_list',
    })


# ==========================================
# LEAD MANAGEMENT
# ==========================================
@login_required
def lead_list_view(request):
    qs = get_scoped_queryset(request.user, Lead.objects.all())

    # Search: Lead Name, Company, Status, Assigned User (PDF Section 17.13)
    search_q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    priority_filter = request.GET.get('priority', '').strip()
    owner_filter = request.GET.get('owner', '').strip()

    if search_q:
        qs = qs.filter(
            Q(name__icontains=search_q) |
            Q(company_name__icontains=search_q) |
            Q(email__icontains=search_q) |
            Q(phone__icontains=search_q) |
            Q(lead_code__icontains=search_q)
        )

    if status_filter:
        qs = qs.filter(status=status_filter)

    if priority_filter:
        qs = qs.filter(priority=priority_filter)

    if owner_filter and (request.user.is_admin_role or request.user.is_manager_role):
        qs = qs.filter(assigned_to_id=owner_filter)

    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    sales_users = User.objects.filter(is_active=True)

    return render(request, 'crm/lead_list.html', {
        'page_obj': page_obj,
        'search_q': search_q,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'owner_filter': owner_filter,
        'sales_users': sales_users,
    })


@login_required
def lead_detail_view(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    if not can_manage_record(request.user, lead):
        messages.error(request, "Access denied: You can only view leads assigned to you.")
        return redirect('lead_list')

    followups = lead.followups.all()
    activities = lead.activities.all()
    audit_logs = AuditLog.objects.filter(entity_name='Lead', record_id=str(lead.id))

    return render(request, 'crm/lead_detail.html', {
        'lead': lead,
        'followups': followups,
        'activities': activities,
        'audit_logs': audit_logs,
    })


@login_required
def lead_create_view(request):
    if request.method == 'POST':
        form = LeadForm(request.POST, user=request.user)
        if form.is_valid():
            lead = form.save(commit=False)
            if not lead.assigned_to:
                lead.assigned_to = request.user
            lead.save()

            AuditLog.log(
                action='CREATE',
                entity_name='Lead',
                record_id=str(lead.id),
                user=request.user,
                new_value={
                    'name': lead.name,
                    'code': lead.lead_code,
                    'status': lead.status,
                    'source': lead.source,
                    'assigned_to': str(lead.assigned_to),
                },
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Lead '{lead.name}' created by {request.user.username}."
            )
            messages.success(request, f"Lead '{lead.name}' created successfully ({lead.lead_code}).")
            return redirect('lead_detail', lead_id=lead.id)
    else:
        form = LeadForm(user=request.user)

    return render(request, 'crm/lead_form.html', {'form': form, 'title': 'Create New Lead'})


@login_required
def lead_edit_view(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    if not can_manage_record(request.user, lead):
        messages.error(request, "Access denied: You do not have permission to modify this lead.")
        return redirect('lead_list')

    old_data = {
        'name': lead.name,
        'status': lead.status,
        'priority': lead.priority,
        'assigned_to': str(lead.assigned_to),
        'expected_value': float(lead.expected_value),
    }

    if request.method == 'POST':
        form = LeadForm(request.POST, instance=lead, user=request.user)
        if form.is_valid():
            updated_lead = form.save()
            new_data = {
                'name': updated_lead.name,
                'status': updated_lead.status,
                'priority': updated_lead.priority,
                'assigned_to': str(updated_lead.assigned_to),
                'expected_value': float(updated_lead.expected_value),
            }
            action_type = 'STATUS_CHANGE' if old_data['status'] != new_data['status'] else 'UPDATE'
            AuditLog.log(
                action=action_type,
                entity_name='Lead',
                record_id=str(updated_lead.id),
                user=request.user,
                old_value=old_data,
                new_value=new_data,
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Lead '{updated_lead.name}' updated by {request.user.username}."
            )
            messages.success(request, f"Lead '{updated_lead.name}' updated successfully.")
            return redirect('lead_detail', lead_id=updated_lead.id)
    else:
        form = LeadForm(instance=lead, user=request.user)

    return render(request, 'crm/lead_form.html', {'form': form, 'title': f"Edit Lead: {lead.name}", 'lead': lead})


@login_required
def lead_delete_view(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    if not can_manage_record(request.user, lead):
        messages.error(request, "Access denied.")
        return redirect('lead_list')

    if request.method == 'POST':
        l_name = lead.name
        l_id = lead.id
        AuditLog.log(
            action='DELETE',
            entity_name='Lead',
            record_id=str(l_id),
            user=request.user,
            old_value={'name': l_name, 'code': lead.lead_code},
            result='SUCCESS',
            ip_address=get_client_ip(request),
            details=f"Lead '{l_name}' deleted by {request.user.username}."
        )
        lead.delete()
        messages.success(request, f"Lead '{l_name}' was deleted.")
        return redirect('lead_list')

    return render(request, 'crm/confirm_delete.html', {
        'object_name': f"Lead: {lead.name} ({lead.lead_code})",
        'cancel_url': 'lead_list',
    })


@login_required
def lead_convert_view(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    if not can_manage_record(request.user, lead):
        messages.error(request, "Access denied.")
        return redirect('lead_list')

    if lead.status == 'Converted':
        messages.warning(request, "This lead has already been converted.")
        return redirect('lead_detail', lead_id=lead.id)

    if request.method == 'POST':
        form = LeadConversionForm(request.POST)
        if form.is_valid():
            # 1. Create Customer
            c_name = form.cleaned_data['customer_name']
            c_email = form.cleaned_data['email']
            c_phone = form.cleaned_data['phone']
            c_company = form.cleaned_data['company_name']

            customer, created = Customer.objects.get_or_create(
                email=c_email,
                defaults={
                    'name': c_name,
                    'phone': c_phone,
                    'company_name': c_company,
                    'status': 'Active',
                    'assigned_to': lead.assigned_to or request.user,
                }
            )

            # 2. Optionally Create Opportunity
            created_opp = None
            if form.cleaned_data.get('create_opportunity'):
                opp_name = form.cleaned_data['opportunity_name']
                opp_amt = form.cleaned_data['opportunity_amount']
                close_date = form.cleaned_data['expected_close_date']

                created_opp = Opportunity.objects.create(
                    name=opp_name,
                    customer=customer,
                    lead=lead,
                    amount=opp_amt,
                    stage='Qualification',
                    probability=50,
                    expected_close_date=close_date,
                    assigned_to=lead.assigned_to or request.user,
                    source=lead.source,
                )

            # 3. Update Lead
            lead.status = 'Converted'
            lead.converted_customer = customer
            if created_opp:
                lead.converted_opportunity = created_opp
            lead.save()

            # 4. Audit Log
            AuditLog.log(
                action='LEAD_CONVERSION',
                entity_name='Lead',
                record_id=str(lead.id),
                user=request.user,
                new_value={
                    'lead_id': lead.id,
                    'customer_id': customer.id,
                    'customer_name': customer.name,
                    'opportunity_id': created_opp.id if created_opp else None,
                },
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Lead '{lead.name}' successfully converted into customer '{customer.name}' by {request.user.username}."
            )

            messages.success(request, f"Lead successfully converted into Customer '{customer.name}'!")
            return redirect('customer_detail', customer_id=customer.id)
    else:
        # Prepopulate with lead info
        initial = {
            'customer_name': lead.name,
            'email': lead.email,
            'phone': lead.phone,
            'company_name': lead.company_name,
            'opportunity_name': f"Deal with {lead.company_name or lead.name}",
            'opportunity_amount': lead.expected_value if lead.expected_value > 0 else 5000.00,
            'expected_close_date': (timezone.localdate() + timedelta(days=30)).strftime('%Y-%m-%d'),
        }
        form = LeadConversionForm(initial=initial)

    return render(request, 'crm/lead_convert.html', {'form': form, 'lead': lead})


# ==========================================
# OPPORTUNITY MANAGEMENT
# ==========================================
@login_required
def opportunity_list_view(request):
    qs = get_scoped_queryset(request.user, Opportunity.objects.all())

    # Search: Opportunity Name, Customer, Stage, Status (PDF Section 17.13)
    search_q = request.GET.get('q', '').strip()
    stage_filter = request.GET.get('stage', '').strip()
    status_filter = request.GET.get('status', '').strip()
    owner_filter = request.GET.get('owner', '').strip()

    if search_q:
        qs = qs.filter(
            Q(name__icontains=search_q) |
            Q(customer__name__icontains=search_q) |
            Q(opportunity_code__icontains=search_q)
        )

    if stage_filter:
        qs = qs.filter(stage=stage_filter)

    if status_filter:
        qs = qs.filter(status=status_filter)

    if owner_filter and (request.user.is_admin_role or request.user.is_manager_role):
        qs = qs.filter(assigned_to_id=owner_filter)

    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    sales_users = User.objects.filter(is_active=True)
    stages = [c[0] for c in Opportunity.STAGE_CHOICES]

    return render(request, 'crm/opportunity_list.html', {
        'page_obj': page_obj,
        'search_q': search_q,
        'stage_filter': stage_filter,
        'status_filter': status_filter,
        'owner_filter': owner_filter,
        'sales_users': sales_users,
        'stages': stages,
    })


@login_required
def opportunity_detail_view(request, opportunity_id):
    opportunity = get_object_or_404(Opportunity, id=opportunity_id)
    if not can_manage_record(request.user, opportunity):
        messages.error(request, "Access denied: You can only view opportunities assigned to you.")
        return redirect('opportunity_list')

    followups = opportunity.followups.all()
    audit_logs = AuditLog.objects.filter(entity_name='Opportunity', record_id=str(opportunity.id))

    return render(request, 'crm/opportunity_detail.html', {
        'opportunity': opportunity,
        'followups': followups,
        'audit_logs': audit_logs,
    })


@login_required
def opportunity_create_view(request):
    if request.method == 'POST':
        form = OpportunityForm(request.POST, user=request.user)
        if form.is_valid():
            opp = form.save(commit=False)
            if not opp.assigned_to:
                opp.assigned_to = request.user
            opp.save()

            AuditLog.log(
                action='CREATE',
                entity_name='Opportunity',
                record_id=str(opp.id),
                user=request.user,
                new_value={
                    'name': opp.name,
                    'code': opp.opportunity_code,
                    'amount': float(opp.amount),
                    'stage': opp.stage,
                    'probability': opp.probability,
                    'expected_close_date': str(opp.expected_close_date),
                    'customer': str(opp.customer),
                },
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Opportunity '{opp.name}' (${opp.amount}) created by {request.user.username}."
            )
            messages.success(request, f"Opportunity '{opp.name}' created successfully.")
            return redirect('opportunity_detail', opportunity_id=opp.id)
    else:
        form = OpportunityForm(user=request.user)

    return render(request, 'crm/opportunity_form.html', {'form': form, 'title': 'Create New Opportunity'})


@login_required
def opportunity_edit_view(request, opportunity_id):
    opportunity = get_object_or_404(Opportunity, id=opportunity_id)
    if not can_manage_record(request.user, opportunity):
        messages.error(request, "Access denied.")
        return redirect('opportunity_list')

    old_data = {
        'name': opportunity.name,
        'amount': float(opportunity.amount),
        'stage': opportunity.stage,
        'probability': opportunity.probability,
        'status': opportunity.status,
    }

    if request.method == 'POST':
        form = OpportunityForm(request.POST, instance=opportunity, user=request.user)
        if form.is_valid():
            updated_opp = form.save()
            new_data = {
                'name': updated_opp.name,
                'amount': float(updated_opp.amount),
                'stage': updated_opp.stage,
                'probability': updated_opp.probability,
                'status': updated_opp.status,
            }
            action_type = 'STATUS_CHANGE' if old_data['stage'] != new_data['stage'] else 'UPDATE'
            AuditLog.log(
                action=action_type,
                entity_name='Opportunity',
                record_id=str(updated_opp.id),
                user=request.user,
                old_value=old_data,
                new_value=new_data,
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Opportunity '{updated_opp.name}' updated by {request.user.username}."
            )
            messages.success(request, f"Opportunity '{updated_opp.name}' updated successfully.")
            return redirect('opportunity_detail', opportunity_id=updated_opp.id)
    else:
        form = OpportunityForm(instance=opportunity, user=request.user)

    return render(request, 'crm/opportunity_form.html', {'form': form, 'title': f"Edit Opportunity: {opportunity.name}", 'opportunity': opportunity})


@login_required
def opportunity_delete_view(request, opportunity_id):
    opportunity = get_object_or_404(Opportunity, id=opportunity_id)
    if not can_manage_record(request.user, opportunity):
        messages.error(request, "Access denied.")
        return redirect('opportunity_list')

    if request.method == 'POST':
        opp_name = opportunity.name
        opp_id = opportunity.id
        AuditLog.log(
            action='DELETE',
            entity_name='Opportunity',
            record_id=str(opp_id),
            user=request.user,
            old_value={'name': opp_name, 'amount': float(opportunity.amount)},
            result='SUCCESS',
            ip_address=get_client_ip(request),
            details=f"Opportunity '{opp_name}' deleted by {request.user.username}."
        )
        opportunity.delete()
        messages.success(request, f"Opportunity '{opp_name}' was deleted.")
        return redirect('opportunity_list')

    return render(request, 'crm/confirm_delete.html', {
        'object_name': f"Opportunity: {opportunity.name} (${opportunity.amount})",
        'cancel_url': 'opportunity_list',
    })


# ==========================================
# FOLLOW-UP MANAGEMENT
# ==========================================
@login_required
def followup_list_view(request):
    qs = get_scoped_queryset(request.user, FollowUp.objects.all())
    today = timezone.localdate()

    # Filters: Date, Status, Assigned User, Related (PDF Section 17.13)
    tab = request.GET.get('tab', 'all')
    status_filter = request.GET.get('status', '').strip()
    type_filter = request.GET.get('type', '').strip()
    owner_filter = request.GET.get('owner', '').strip()
    search_q = request.GET.get('q', '').strip()

    if tab == 'today':
        qs = qs.filter(follow_up_date=today, status='Planned')
    elif tab == 'overdue':
        qs = qs.filter(follow_up_date__lt=today, status='Planned')
    elif tab == 'upcoming':
        qs = qs.filter(follow_up_date__gt=today, status='Planned')
    elif tab == 'completed':
        qs = qs.filter(status='Completed')

    if status_filter:
        qs = qs.filter(status=status_filter)

    if type_filter:
        qs = qs.filter(follow_up_type=type_filter)

    if owner_filter and (request.user.is_admin_role or request.user.is_manager_role):
        qs = qs.filter(assigned_to_id=owner_filter)

    if search_q:
        qs = qs.filter(
            Q(subject__icontains=search_q) |
            Q(remarks__icontains=search_q) |
            Q(customer__name__icontains=search_q) |
            Q(lead__name__icontains=search_q)
        )

    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    sales_users = User.objects.filter(is_active=True)
    types = [c[0] for c in FollowUp.TYPE_CHOICES]

    return render(request, 'crm/followup_list.html', {
        'page_obj': page_obj,
        'tab': tab,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'owner_filter': owner_filter,
        'search_q': search_q,
        'sales_users': sales_users,
        'types': types,
    })


@login_required
def followup_create_view(request):
    if request.method == 'POST':
        form = FollowUpForm(request.POST, user=request.user)
        if form.is_valid():
            followup = form.save(commit=False)
            if not followup.assigned_to:
                followup.assigned_to = request.user
            followup.save()

            AuditLog.log(
                action='CREATE',
                entity_name='FollowUp',
                record_id=str(followup.id),
                user=request.user,
                new_value={
                    'subject': followup.subject,
                    'type': followup.follow_up_type,
                    'date': str(followup.follow_up_date),
                    'status': followup.status,
                    'assigned_to': str(followup.assigned_to),
                },
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Follow-up '{followup.subject}' scheduled by {request.user.username}."
            )
            messages.success(request, f"Follow-up '{followup.subject}' scheduled.")
            return redirect('followup_list')
    else:
        # Check initial params from query string (e.g. customer_id, lead_id)
        initial = {}
        if 'customer' in request.GET:
            initial['customer'] = request.GET.get('customer')
        if 'lead' in request.GET:
            initial['lead'] = request.GET.get('lead')
        form = FollowUpForm(initial=initial, user=request.user)

    return render(request, 'crm/followup_form.html', {'form': form, 'title': 'Schedule Follow-Up'})


@login_required
def followup_complete_view(request, followup_id):
    followup = get_object_or_404(FollowUp, id=followup_id)
    if not can_manage_record(request.user, followup):
        messages.error(request, "Access denied.")
        return redirect('followup_list')

    if request.method == 'POST':
        completion_notes = request.POST.get('completion_notes', '').strip()
        followup.status = 'Completed'
        if completion_notes:
            followup.remarks += f"\n[Completed on {timezone.now().strftime('%Y-%m-%d %H:%M')}: {completion_notes}]"
        followup.save(update_fields=['status', 'remarks'])

        # Create Activity Record
        Activity.objects.create(
            activity_type=followup.follow_up_type if followup.follow_up_type in ['Call', 'Meeting', 'Email', 'Task'] else 'Task',
            subject=f"Completed Follow-up: {followup.subject}",
            description=completion_notes or followup.remarks,
            customer=followup.customer,
            lead=followup.lead,
            assigned_to=followup.assigned_to or request.user,
            status='Completed'
        )

        AuditLog.log(
            action='UPDATE',
            entity_name='FollowUp',
            record_id=str(followup.id),
            user=request.user,
            new_value={'status': 'Completed', 'notes': completion_notes},
            result='SUCCESS',
            ip_address=get_client_ip(request),
            details=f"Follow-up '{followup.subject}' marked as Completed by {request.user.username}."
        )
        messages.success(request, f"Follow-up '{followup.subject}' marked as completed.")
        return redirect('followup_list')

    return render(request, 'crm/followup_complete.html', {'followup': followup})


@login_required
def followup_reschedule_view(request, followup_id):
    followup = get_object_or_404(FollowUp, id=followup_id)
    if not can_manage_record(request.user, followup):
        messages.error(request, "Access denied.")
        return redirect('followup_list')

    if request.method == 'POST':
        form = FollowUpRescheduleForm(request.POST)
        if form.is_valid():
            new_date = form.cleaned_data['new_date']
            new_time = form.cleaned_data['new_time']
            reason = form.cleaned_data['reschedule_reason']

            old_date_str = str(followup.follow_up_date)
            followup.follow_up_date = new_date
            if new_time:
                followup.follow_up_time = new_time
            followup.remarks += f"\n[Rescheduled from {old_date_str} to {new_date}: {reason}]"
            followup.status = 'Planned'
            followup.save()

            AuditLog.log(
                action='RESCHEDULE',
                entity_name='FollowUp',
                record_id=str(followup.id),
                user=request.user,
                old_value={'date': old_date_str},
                new_value={'date': str(new_date), 'reason': reason},
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Follow-up '{followup.subject}' rescheduled from {old_date_str} to {new_date} by {request.user.username}."
            )
            messages.success(request, f"Follow-up successfully rescheduled to {new_date}.")
            return redirect('followup_list')
    else:
        form = FollowUpRescheduleForm(initial={'new_date': followup.follow_up_date})

    return render(request, 'crm/followup_reschedule.html', {'form': form, 'followup': followup})


# ==========================================
# ACTIVITY MANAGEMENT
# ==========================================
@login_required
def activity_list_view(request):
    qs = get_scoped_queryset(request.user, Activity.objects.all())

    type_filter = request.GET.get('type', '').strip()
    status_filter = request.GET.get('status', '').strip()
    owner_filter = request.GET.get('owner', '').strip()

    if type_filter:
        qs = qs.filter(activity_type=type_filter)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if owner_filter and (request.user.is_admin_role or request.user.is_manager_role):
        qs = qs.filter(assigned_to_id=owner_filter)

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    types = [c[0] for c in Activity.TYPE_CHOICES]
    sales_users = User.objects.filter(is_active=True)

    return render(request, 'crm/activity_list.html', {
        'page_obj': page_obj,
        'types': types,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'owner_filter': owner_filter,
        'sales_users': sales_users,
    })


@login_required
def activity_create_view(request):
    if request.method == 'POST':
        form = ActivityForm(request.POST)
        if form.is_valid():
            act = form.save(commit=False)
            if not act.assigned_to:
                act.assigned_to = request.user
            act.save()

            AuditLog.log(
                action='CREATE',
                entity_name='Activity',
                record_id=str(act.id),
                user=request.user,
                new_value={'type': act.activity_type, 'subject': act.subject},
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Activity '{act.subject}' logged by {request.user.username}."
            )
            messages.success(request, f"Activity '{act.subject}' logged successfully.")
            return redirect('activity_list')
    else:
        form = ActivityForm(initial={'activity_date': timezone.now().strftime('%Y-%m-%dT%H:%M')})

    return render(request, 'crm/activity_form.html', {'form': form, 'title': 'Log New Activity'})
