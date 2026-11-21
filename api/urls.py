from django.urls import path
from . import views
from .doc_views import api_docs_view

urlpatterns = [
    # API Docs
    path('docs/', api_docs_view, name='api_docs'),

    # Auth
    path('auth/login', views.LoginAPIView.as_view(), name='api_login'),
    path('auth/logout', views.LogoutAPIView.as_view(), name='api_logout'),

    # Customers
    path('customers', views.CustomerListCreateAPIView.as_view(), name='api_customers'),
    path('customers/<int:pk>', views.CustomerDetailAPIView.as_view(), name='api_customer_detail'),

    # Leads
    path('leads', views.LeadListCreateAPIView.as_view(), name='api_leads'),

    # Opportunities
    path('opportunities', views.OpportunityListCreateAPIView.as_view(), name='api_opportunities'),

    # Follow-Ups
    path('followups', views.FollowUpListCreateAPIView.as_view(), name='api_followups'),

    # Reports
    path('reports/pipeline', views.PipelineReportAPIView.as_view(), name='api_report_pipeline'),
]
