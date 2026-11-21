from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Customers
    path('customers/', views.customer_list_view, name='customer_list'),
    path('customers/create/', views.customer_create_view, name='customer_create'),
    path('customers/<int:customer_id>/', views.customer_detail_view, name='customer_detail'),
    path('customers/<int:customer_id>/edit/', views.customer_edit_view, name='customer_edit'),
    path('customers/<int:customer_id>/delete/', views.customer_delete_view, name='customer_delete'),

    # Leads
    path('leads/', views.lead_list_view, name='lead_list'),
    path('leads/create/', views.lead_create_view, name='lead_create'),
    path('leads/<int:lead_id>/', views.lead_detail_view, name='lead_detail'),
    path('leads/<int:lead_id>/edit/', views.lead_edit_view, name='lead_edit'),
    path('leads/<int:lead_id>/delete/', views.lead_delete_view, name='lead_delete'),
    path('leads/<int:lead_id>/convert/', views.lead_convert_view, name='lead_convert'),

    # Opportunities
    path('opportunities/', views.opportunity_list_view, name='opportunity_list'),
    path('opportunities/create/', views.opportunity_create_view, name='opportunity_create'),
    path('opportunities/<int:opportunity_id>/', views.opportunity_detail_view, name='opportunity_detail'),
    path('opportunities/<int:opportunity_id>/edit/', views.opportunity_edit_view, name='opportunity_edit'),
    path('opportunities/<int:opportunity_id>/delete/', views.opportunity_delete_view, name='opportunity_delete'),

    # Follow-Ups
    path('followups/', views.followup_list_view, name='followup_list'),
    path('followups/create/', views.followup_create_view, name='followup_create'),
    path('followups/<int:followup_id>/complete/', views.followup_complete_view, name='followup_complete'),
    path('followups/<int:followup_id>/reschedule/', views.followup_reschedule_view, name='followup_reschedule'),

    # Activities
    path('activities/', views.activity_list_view, name='activity_list'),
    path('activities/create/', views.activity_create_view, name='activity_create'),
]
