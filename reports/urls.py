from django.urls import path
from . import views

urlpatterns = [
    path('', views.report_center_view, name='report_center'),
    path('customers/', views.customer_report_view, name='customer_report'),
    path('leads/', views.lead_report_view, name='lead_report'),
    path('followups/', views.followup_report_view, name='followup_report'),
    path('opportunities/', views.opportunity_report_view, name='opportunity_report'),
    path('pipeline/', views.pipeline_report_view, name='pipeline_report'),
    path('conversion/', views.conversion_report_view, name='conversion_report'),
    path('user-activity/', views.user_activity_report_view, name='user_activity_report'),
]
