from django.contrib import admin
from .models import Customer, Lead, Opportunity, FollowUp, Activity


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_code', 'name', 'email', 'phone', 'company_name', 'status', 'assigned_to', 'created_at')
    list_filter = ('status', 'assigned_to', 'created_at')
    search_fields = ('customer_code', 'name', 'email', 'phone', 'company_name')


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('lead_code', 'name', 'company_name', 'source', 'status', 'priority', 'expected_value', 'assigned_to', 'created_at')
    list_filter = ('status', 'priority', 'source', 'assigned_to')
    search_fields = ('lead_code', 'name', 'email', 'phone', 'company_name')


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ('opportunity_code', 'name', 'customer', 'amount', 'stage', 'probability', 'expected_close_date', 'status', 'assigned_to')
    list_filter = ('stage', 'status', 'assigned_to', 'expected_close_date')
    search_fields = ('opportunity_code', 'name', 'customer__name')


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('subject', 'follow_up_type', 'follow_up_date', 'status', 'customer', 'lead', 'assigned_to')
    list_filter = ('status', 'follow_up_type', 'follow_up_date', 'assigned_to')
    search_fields = ('subject', 'remarks', 'customer__name', 'lead__name')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('subject', 'activity_type', 'activity_date', 'status', 'customer', 'lead', 'assigned_to')
    list_filter = ('activity_type', 'status', 'activity_date')
    search_fields = ('subject', 'description')
