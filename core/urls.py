# core/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.urls import reverse_lazy

app_name = 'core'

urlpatterns = [
    # --- Admin & Super Admin ---
    path('admin-login/', views.login_admin_view, name='login_admin'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', auth_views.LogoutView.as_view(next_page='core:login_admin'), name='admin_logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_view, name='profile_update'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    
    # --- ADMIN PASSWORD RESET URLS (Fixed) ---
    path('admin-reset/password/', 
         auth_views.PasswordResetView.as_view(
             template_name="core/admin_password_reset_form.html",
             success_url=reverse_lazy('core:admin_password_reset_done'),
             email_template_name='core/admin_password_reset_email.html',
             subject_template_name='core/admin_password_reset_subject.txt'
         ), 
         name='admin_password_reset'),

    path('admin-reset/password/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name="core/admin_password_reset_done.html"
         ), 
         name='admin_password_reset_done'),

    path('admin-reset/confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name="core/admin_password_reset_confirm.html",
             success_url=reverse_lazy('core:admin_password_reset_complete')
         ), 
         name='admin_password_reset_confirm'),

    path('admin-reset/complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name="core/admin_password_reset_complete.html"
         ), 
         name='admin_password_reset_complete'),

    # --- Client URLs ---
    path('register/', views.client_register_view, name='client_register'),
    path('', views.client_login_view, name='client_login'),
    path('client/dashboard/', views.client_dashboard_view, name='client_dashboard'),
    path('client-assignments/', views.client_assignment_view, name='client_assignments'),   
    path('client/logout/', auth_views.LogoutView.as_view(next_page='core:client_login'), name='client_logout'),    
    
    
    path('admin-calendar/', views.admin_calendar_view, name='admin_calendar'),    
    path('reports/rejection/', views.rejection_report_view, name='report_rejection'),
    path('reports/activity/', views.client_activity_report_view, name='report_activity'),
    
    # --- NOTIFICATION URLS ---
    path('notifications/get-unread/', views.get_unread_notifications, name='get_unread'),
    path('notifications/read/<int:notif_id>/', views.mark_notification_as_read, name='mark_as_read'),
    
    path('client/calendar/', views.client_calendar_view, name='client_calendar'),
    
    path('client/history/', views.client_post_history_view, name='client_post_history'),
    
    path('client/analytics/', views.client_analytics_view, name='client_analytics'),
    
    path('client/profile/', views.client_profile_view, name='client_profile'),
    
    path('client/feed/', views.client_feed_view, name='client_feed'),
        
    path('client/pending/', views.client_pending_approval_view, name='client_pending_approval'),
    
    # --- PASSWORD RESET URLS ---
    
    # 1. The page where the user enters their email
    path('reset-password/', 
         auth_views.PasswordResetView.as_view(
             template_name="core/password_reset_form.html",
             success_url=reverse_lazy('core:password_reset_done'),
             
             email_template_name='core/password_reset_email.html',
             subject_template_name='core/password_reset_subject.txt'
         ), 
         name='password_reset'),

    # 2. The "success" page telling them to check their email
    path('reset-password/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name="core/password_reset_done.html"
         ), 
         name='password_reset_done'),

    # 3. The link from the email, where they enter a new password
    path('reset-password/confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name="core/password_reset_confirm.html",
             success_url=reverse_lazy('core:password_reset_complete')
         ), 
         name='password_reset_confirm'),

    # 4. The "complete" page saying their password was changed
    path('reset-password/complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name="core/password_reset_complete.html"
         ), 
         name='password_reset_complete')
    
]