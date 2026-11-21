from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('users/', views.user_list_view, name='user_list'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit_view, name='user_edit'),
    path('users/<int:user_id>/toggle-status/', views.user_toggle_status_view, name='user_toggle_status'),
    path('users/<int:user_id>/unlock/', views.user_unlock_view, name='user_unlock'),
    path('users/<int:user_id>/reset-password/', views.user_reset_password_view, name='user_reset_password'),
    path('audit-log/', views.audit_log_list_view, name='audit_log_list'),
]
