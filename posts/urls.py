# posts/urls.py

from django.urls import path
from . import views

app_name = 'posts'

urlpatterns = [
    path('create/', views.create_post_view, name='create_post'),
    path('review/', views.client_review_post_view, name='client_review_post'),
    path('view/<int:post_id>/', views.view_post_view, name='view_post'),
    path('edit/<int:post_id>/', views.edit_post_view, name='edit_post'),
    path('delete/<int:post_id>/', views.delete_post_view, name='delete_post'),
    path('list/', views.post_list_view, name='post_list'), 
    path('request/', views.request_post_view, name='request_post'),
    path('<int:post_id>/', views.client_post_detail_view, name='client_post_detail'),
    path('admin/requests/', views.admin_post_request_list_view, name='admin_request_list'),
    path('mark-pending/<int:post_id>/', views.mark_post_pending_view, name='mark_post_pending'),

    
]