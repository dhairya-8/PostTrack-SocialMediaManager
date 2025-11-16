# core/views.py

# Standard library imports
import json
import csv
import io
import datetime

# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone

# App-specific model imports
from users.models import User, ClientProfile
from posts.models import Post, Feedback, Rating
from reports.models import GeneratedReport
from core.models import *
from posts.models import *

# Import for complex queries
from django.db.models import Q, Count, F, Avg

# Forms
from .forms import ClientRegistrationForm, ClientProfileUpdateForm, ClientPasswordChangeForm

# --- ADMIN & SUPER ADMIN VIEWS ---

def login_admin_view(request):
    """
    Handles the login for Admin and Super Admin users.
    """
    if request.user.is_authenticated:
        if request.user.role in [User.Role.ADMIN, User.Role.SUPER_ADMIN]:
            return redirect('core:dashboard')
        else:
            logout(request)

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role in [User.Role.ADMIN, User.Role.SUPER_ADMIN]:
                login(request, user)
                messages.success(request, 'Login successful. Welcome back!')
                return redirect('core:dashboard')
            else:
                messages.error(request, 'This login page is for administrators only.')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    else:
        form = AuthenticationForm()
        messages.info(request, 'Logged out, Please log in with your administrator credentials.')
    return render(request, 'core/login_admin.html', {'form': form})

def is_admin_or_superadmin(user):
    return user.is_authenticated and user.role in [User.Role.ADMIN, User.Role.SUPER_ADMIN]

@login_required(login_url='core:login_admin')
def profile_view(request):
    """
    Displays and updates the profile for Admin/SuperAdmin.
    """
    user = request.user

    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()
        theme = request.POST.get('theme', 'light')

        user.phone_number = phone_number
        user.theme = theme
        user.save()

        messages.success(request, 'Your profile has been updated successfully!')
        return redirect('core:profile')

    return render(request, 'core/profile_admin.html', {'user': user})

@login_required(login_url='core:login_admin')
def change_password_view(request):
    """
    Allows Admin/SuperAdmin to change password.
    After successful change, user is logged out.
    """
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        user = request.user

        # 1️⃣ Validate current password
        if not user.check_password(current_password):
            messages.error(request, 'Your current password is incorrect.')
            return redirect('core:profile')

        # 2️⃣ Validate new password match
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('core:profile')

        # 3️⃣ Prevent reusing the same password
        if current_password == new_password:
            messages.warning(request, 'New password cannot be the same as the old password.')
            return redirect('core:profile')

        # 4️⃣ Set new password
        user.set_password(new_password)
        user.save()

        # 5️⃣ Log out after successful change
        logout(request)
        messages.success(request, 'Password changed successfully. Please log in again.')
        return redirect('core:login_admin')

    return redirect('core:profile')

@user_passes_test(is_admin_or_superadmin, login_url='core:login_admin')
def dashboard_view(request):
    """
    Dashboard view for Admin and Super Admin users.
    Admin: sees rejected posts + feedback.
    Super Admin: sees overall platform metrics.
    """

    # Auto-update approved posts that reached their scheduled time
    Post.objects.filter(
        status=Post.Status.APPROVED, 
        scheduled_datetime__lte=timezone.now()
    ).update(status=Post.Status.PUBLISHED)

    user = request.user

    # Base query: depends on role
    if user.role == User.Role.SUPER_ADMIN:
        all_posts = Post.objects.all()
        recent_feedback = Feedback.objects.all().order_by('-created_at')[:5]
    else:
        admin_clients = ClientProfile.objects.filter(assigned_admins=user)
        all_posts = Post.objects.filter(assigned_client__in=admin_clients)
        recent_feedback = Feedback.objects.filter(
            post__in=all_posts
        ).order_by('-created_at')[:5]

    # Basic counts
    pending_count = all_posts.filter(status=Post.Status.PENDING).count()
    rejected_count = all_posts.filter(status=Post.Status.REJECTED).count()
    approved_count = all_posts.filter(status=Post.Status.APPROVED).count()
    published_count = all_posts.filter(status=Post.Status.PUBLISHED).count()
    draft_count = all_posts.filter(status=Post.Status.DRAFT).count()

    context = {
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        'approved_count': approved_count,
        'published_count': published_count,
        'draft_count': draft_count,
        'recent_feedback': recent_feedback,
    }

    # Role-based extras
    if user.role == User.Role.ADMIN:
        context['rejected_posts'] = all_posts.filter(
            status=Post.Status.REJECTED
        ).prefetch_related('feedback')

    elif user.role == User.Role.SUPER_ADMIN:
        context.update({
            'total_posts': Post.objects.count(),
            'total_clients': ClientProfile.objects.count(),
            'total_admins': User.objects.filter(role=User.Role.ADMIN).count(),
        })

    return render(request, 'core/index.html', context)

# --- CLIENT VIEWS ---

def client_register_view(request):
    if request.user.is_authenticated:
        if request.user.role == User.Role.CLIENT:
            return redirect('core:client_dashboard')
        else:
            return redirect('core:dashboard')

    if request.method == 'POST':
        form = ClientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful. Please log in to continue.')
            return redirect('core:client_login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ClientRegistrationForm()
        
    return render(request, 'core/register_client.html', {'form': form})

            
def client_login_view(request):
    if request.user.is_authenticated:
        if request.user.role == User.Role.CLIENT:
            return redirect('core:client_dashboard')
        else:
            messages.error(request, 'Logged out due to role mismatch.')
            logout(request)

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role == User.Role.CLIENT:
                login(request, user)
                messages.success(request, 'Login successful. Welcome back!')
                return redirect('core:client_dashboard')
            else:
                messages.error(request, 'This login page is for clients only.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        messages.info(request, 'Please log in with your client credentials.')
        form = AuthenticationForm()
        
    return render(request, 'core/login_client.html', {'form': form})

def is_client(user):
    return user.is_authenticated and user.role == User.Role.CLIENT

@user_passes_test(is_client, login_url='core:client_login')
def client_dashboard_view(request):
    """
    Displays the main client landing page/dashboard.
    """
    # Auto-update scheduled posts
    Post.objects.filter(
        assigned_client=request.user.client_profile,
        status=Post.Status.APPROVED, 
        scheduled_datetime__lte=timezone.now()
    ).update(status=Post.Status.PUBLISHED)
    
    client_profile = request.user.client_profile
    
    # 1. Get Posts for "Pending Approval"
    pending_posts = Post.objects.filter(
        assigned_client=client_profile,
        status=Post.Status.PENDING
    ).order_by('scheduled_datetime')
    pending_posts_preview = pending_posts[:4] # Preview list
    
    # 2. Get Stats
    approved_count = Post.objects.filter(assigned_client=client_profile, status=Post.Status.APPROVED).count()
    scheduled_count = Post.objects.filter(
        assigned_client=client_profile, 
        status__in=[Post.Status.APPROVED, Post.Status.PUBLISHED],
        scheduled_datetime__gte=timezone.now()
    ).count()
    rejected_count = Post.objects.filter(assigned_client=client_profile, status=Post.Status.REJECTED).count()

    # 3. Get Other Sections
    recent_activity = AuditLog.objects.filter(user=request.user).order_by('-timestamp')[:3]
    upcoming_posts = Post.objects.filter(
        assigned_client=client_profile,
        status__in=[Post.Status.APPROVED, Post.Status.PUBLISHED],
        scheduled_datetime__gte=timezone.now()
    ).order_by('scheduled_datetime')[:3]
    
    # --- 4. THIS SECTION IS UPDATED ---
    # Get Published Post Feed (Preview)
    published_posts_query = Post.objects.filter(
        assigned_client=client_profile, 
        status=Post.Status.PUBLISHED
    ).annotate(
        avg_rating=Avg('ratings__score')
    ).order_by('-scheduled_datetime')

    published_posts_preview = published_posts_query[:3] # Get first 3 for preview
    published_posts_count = published_posts_query.count() # Get total count

    context = {
        'company_name': client_profile.company_name,
        'pending_posts': pending_posts,             # Full list for modals
        'pending_posts_preview': pending_posts_preview, # Limited list for card
        'pending_count': pending_posts.count(),
        'scheduled_count': scheduled_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'recent_activity': recent_activity,
        'upcoming_posts': upcoming_posts,
        
        # --- THESE ARE THE UPDATED CONTEXT VARIABLES ---
        'published_posts': published_posts_preview,  # Pass the preview list
        'published_posts_count': published_posts_count,  # Pass the total count
    }
    return render(request, 'core/client_dashboard.html', context)

def is_superadmin(user):
    return user.is_authenticated and user.role == User.Role.SUPER_ADMIN

@user_passes_test(is_superadmin, login_url='core:login_admin')
def client_assignment_view(request):
    if request.method == 'POST':
        client_id = request.POST.get('client_id')
        admin_ids = request.POST.getlist('admin_ids')
        try:
            client = ClientProfile.objects.get(user_id=client_id)
            client.assigned_admins.set(admin_ids) 
            messages.success(request, f"Admin assignments for {client.company_name} updated successfully.")
        except ClientProfile.DoesNotExist:
            messages.error(request, "Client not found.")
        return redirect('core:client_assignments')

    all_clients = ClientProfile.objects.all().prefetch_related('assigned_admins')
    all_admins = User.objects.filter(role=User.Role.ADMIN)

    context = {
        'all_clients': all_clients,
        'all_admins': all_admins,
    }
    return render(request, 'core/client_assignments.html', context)

@user_passes_test(is_admin_or_superadmin, login_url='core:login_admin')
def admin_calendar_view(request):
    user = request.user
    
    if user.role == User.Role.SUPER_ADMIN:
        all_posts = Post.objects.all()
    else:
        admin_clients = ClientProfile.objects.filter(assigned_admins=user)
        all_posts = Post.objects.filter(assigned_client__in=admin_clients)

    calendar_events = []
    for post in all_posts.filter(scheduled_datetime__isnull=False):
        if post.status == Post.Status.DRAFT:
            className = 'bg-secondary'
        elif post.status == Post.Status.PENDING:
            className = 'bg-warning'
        elif post.status == Post.Status.REJECTED:
            className = 'bg-danger'
        elif post.status == Post.Status.APPROVED:
            className = 'bg-success'
        elif post.status == Post.Status.PUBLISHED:
            className = 'bg-primary'
        else:
            className = 'bg-dark'

        calendar_events.append({
            'title': post.title,
            'start': post.scheduled_datetime.isoformat(),
            'className': f'{className} text-white',
            'id': post.id,
            'url': reverse('posts:edit_post', args=[post.id])
        })

    context = {
        'calendar_events_json': json.dumps(calendar_events)
    }
    return render(request, 'core/admin_calendar.html', context)

@user_passes_test(is_admin_or_superadmin, login_url='core:login_admin')
def rejection_report_view(request):
    user = request.user
    
    if user.role == User.Role.SUPER_ADMIN:
        all_clients = ClientProfile.objects.all()
    else:
        all_clients = ClientProfile.objects.filter(assigned_admins=user)
        
    all_posts = Post.objects.filter(assigned_client__in=all_clients)

    reviewable_posts = all_posts.filter(status__in=[
        Post.Status.PENDING, 
        Post.Status.APPROVED, 
        Post.Status.REJECTED, 
        Post.Status.PUBLISHED
    ])
    total_reviewable_count = reviewable_posts.count()
    total_rejected_count = all_posts.filter(status=Post.Status.REJECTED).count()

    if total_reviewable_count > 0:
        overall_rejection_rate = (total_rejected_count / total_reviewable_count) * 100
    else:
        overall_rejection_rate = 0

    most_rejected_posts = all_posts.annotate(
        rejection_count=Count('feedback')
    ).filter(rejection_count__gt=0).order_by('-rejection_count')[:10]

    clients_by_rejection = all_clients.annotate(
        total_posts=Count('posts'),
        rejected_posts=Count('posts', filter=Q(posts__status=Post.Status.REJECTED))
    ).filter(total_posts__gt=0).annotate(
        rejection_rate= (F('rejected_posts') * 100.0 / F('total_posts'))
    ).order_by('-rejection_rate')

    if request.method == 'POST':
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(['Client Name', 'Rejection Rate (%)', 'Rejected Posts', 'Total Posts'])
        
        for client in clients_by_rejection:
            writer.writerow([
                client.company_name,
                f"{client.rejection_rate:.1f}",
                client.rejected_posts,
                client.total_posts
            ])
            
        csv_buffer.seek(0)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        filename = f"rejection_report_{timestamp}.csv"
        
        report_file = ContentFile(csv_buffer.getvalue().encode('utf-8'))
        
        report = GeneratedReport(
            title=f"Rejection Report - {timestamp}",
            report_type="rejection_rates",
            generated_by=request.user
        )
        report.file.save(filename, report_file)
        report.save()
        
        response = HttpResponse(csv_buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    context = {
        'total_rejected_count': total_rejected_count,
        'overall_rejection_rate': overall_rejection_rate,
        'most_rejected_posts': most_rejected_posts,
        'clients_by_rejection': clients_by_rejection,
    }
    return render(request, 'core/rejection_report.html', context)

@user_passes_test(is_admin_or_superadmin, login_url='core:login_admin')
def client_activity_report_view(request):
    user = request.user
    
    if user.role == User.Role.SUPER_ADMIN:
        all_clients = ClientProfile.objects.all()
    else:
        all_clients = ClientProfile.objects.filter(assigned_admins=user)

    clients_by_feedback = all_clients.annotate(
        feedback_count=Count('user__feedback')
    ).filter(feedback_count__gt=0).order_by('-feedback_count')[:10]

    clients_by_rating = all_clients.annotate(
        average_rating=Avg('user__rating__score')
    ).filter(average_rating__isnull=False).order_by('-average_rating')[:10]
    
    client_posts = Post.objects.filter(assigned_client__in=all_clients)
    
    recent_feedback = Feedback.objects.filter(
        post__in=client_posts
    ).order_by('-created_at')[:10]
    
    recent_ratings = Rating.objects.filter(
        post__in=client_posts
    ).order_by('-created_at')[:10]

    context = {
        'clients_by_feedback': clients_by_feedback,
        'clients_by_rating': clients_by_rating,
        'recent_feedback': recent_feedback,
        'recent_ratings': recent_ratings,
    }
    return render(request, 'core/report_activity.html', context)


# --- NOTIFICATION VIEWS ---

@login_required
def get_unread_notifications(request):
    notifications = Notification.objects.filter(
        recipient=request.user, 
        is_read=False
    )
    count = notifications.count()
    
    notif_list = []
    for notif in notifications[:5]:
        notif_list.append({
            'id': notif.id,
            'message': notif.message,
            'time': notif.timestamp.strftime("%b %d, %Y %I:%M %p")
        })

    return JsonResponse({
        'count': count,
        'notifications': notif_list
    })

@login_required
def mark_notification_as_read(request, notif_id):
    """
    Mark a specific notification as read and redirect to its related post.
    """
    notification = get_object_or_404(
        Notification, 
        id=notif_id, 
        recipient=request.user
    )
    
    notification.is_read = True
    notification.save()
    
    # --- THIS IS THE UPDATED LOGIC ---
    if notification.related_post:
        if request.user.role == User.Role.CLIENT:
            # 1. If it's a "Pending" or "Published" post, go to the detail page
            if notification.related_post.status in [Post.Status.PENDING, Post.Status.PUBLISHED]:
                return redirect('posts:client_post_detail', post_id=notification.related_post.id)
            else:
                # 2. Otherwise (e.g., just approved), go to the main feed
                return redirect('core:client_feed')
        
        else: # This is the Admin
            return redirect('posts:edit_post', post_id=notification.related_post.id)
    
    # 3. Fallback for any notification with no post (e.g., "Welcome!")
    if request.user.role == User.Role.CLIENT:
        return redirect('core:client_dashboard')
    else:
        return redirect('core:dashboard')

# --- ADDITIONAL CLIENT VIEWS ---

@user_passes_test(is_client, login_url='core:client_login')
def client_calendar_view(request):
    """
    Displays the client-side calendar page.
    """
    client_profile = request.user.client_profile

    # 1. Get all posts for this client that have a date
    all_posts = Post.objects.filter(
        assigned_client=client_profile,
        scheduled_datetime__isnull=False
    ).exclude(status=Post.Status.DRAFT) # Exclude drafts

    # 2. Format Posts into Calendar Events
    calendar_events = []
    for post in all_posts:
        # Assign a color based on status
        if post.status == Post.Status.PENDING:
            className = 'bg-warning'
        elif post.status == Post.Status.REJECTED:
            className = 'bg-danger'
        elif post.status == Post.Status.APPROVED:
            className = 'bg-success'
        elif post.status == Post.Status.PUBLISHED:
            className = 'bg-primary'
        else:
            className = 'bg-dark' # Fallback for Archived

        calendar_events.append({
            'title': post.title,
            'start': post.scheduled_datetime.isoformat(),
            'className': f'{className} text-white',
            'id': post.id
        })

    context = {
        'calendar_events_json': json.dumps(calendar_events)
    }

    return render(request, 'core/client_calendar.html', context)

@user_passes_test(is_client, login_url='core:client_login')
def client_post_history_view(request):
    """
    Displays a complete history of all posts for the client.
    """
    client_profile = request.user.client_profile
    
    # Get all posts for this client, excluding drafts, ordered by last update
    all_posts = Post.objects.filter(
        assigned_client=client_profile
    ).exclude(
        status=Post.Status.DRAFT
    ).order_by('-updated_at')

    context = {
        'posts_history': all_posts
    }
    
    return render(request, 'core/client_post_history.html', context)

@user_passes_test(is_client, login_url='core:client_login')
def client_analytics_view(request):
    """
    Displays an analytics dashboard for the client.
    """
    client_profile = request.user.client_profile
    
    # Get all posts for this client, excluding drafts
    all_posts = Post.objects.filter(
        assigned_client=client_profile
    ).exclude(status=Post.Status.DRAFT)

    # --- 1. Get Key Stats ---
    total_posts_count = all_posts.count()
    published_count = all_posts.filter(status=Post.Status.PUBLISHED).count()
    
    # --- 2. Get Rating Stats [cite: 25] ---
    # We filter ratings by the user (client)
    client_ratings = Rating.objects.filter(user=request.user)
    total_ratings_count = client_ratings.count()
    
    avg_rating = client_ratings.aggregate(avg_score=Avg('score'))['avg_score'] or 0

    # --- 3. Get Top Rated Posts ---
    top_rated_posts = all_posts.annotate(
        avg_score=Avg('ratings__score')
    ).filter(avg_score__isnull=False).order_by('-avg_score')[:5]

    # --- 4. Get Most Discussed Posts (by feedback count) ---
    most_discussed_posts = all_posts.annotate(
        comment_count=Count('feedback')
    ).filter(comment_count__gt=0).order_by('-comment_count')[:5]
    
    # --- 5. Data for Chart.js  ---
    status_distribution = {
        'published': published_count,
        'approved': all_posts.filter(status=Post.Status.APPROVED).count(),
        'rejected': all_posts.filter(status=Post.Status.REJECTED).count(),
        'pending': all_posts.filter(status=Post.Status.PENDING).count(),
    }

    context = {
        'total_posts_count': total_posts_count,
        'published_count': published_count,
        'total_ratings_count': total_ratings_count,
        'avg_rating': avg_rating,
        'top_rated_posts': top_rated_posts,
        'most_discussed_posts': most_discussed_posts,
        'status_distribution_json': json.dumps(list(status_distribution.values())),
        'status_labels_json': json.dumps(list(status_distribution.keys())),
    }
    
    return render(request, 'core/client_analytics.html', context)

# --- CLIENT PROFILE VIEW ---

@user_passes_test(is_client, login_url='core:client_login')
def client_profile_view(request):
    """
    Handles the client profile update (User + ClientProfile)
    and password change for clients.
    """
    user = request.user
    client_profile = user.client_profile  # Access linked profile

    if request.method == 'POST':
        # --- PROFILE UPDATE ---
        if 'update_profile' in request.POST:
            profile_form = ClientProfileUpdateForm(request.POST, instance=client_profile, user=user)
            password_form = ClientPasswordChangeForm(user)  # keep unbound
            
            if profile_form.is_valid():
                # Save ClientProfile fields
                profile_form.save()
                
                # Save User's first and last name (from the custom form fields)
                user.first_name = profile_form.cleaned_data.get('first_name')
                user.last_name = profile_form.cleaned_data.get('last_name')
                user.save()
                
                messages.success(request, 'Your profile has been updated successfully.')
                return redirect('core:client_profile')
            else:
                messages.error(request, 'Please correct the errors in your profile details.')
                print(profile_form.errors)

        # --- PASSWORD CHANGE ---
        elif 'change_password' in request.POST:
            password_form = ClientPasswordChangeForm(user, request.POST)
            profile_form = ClientProfileUpdateForm(instance=client_profile, user=user)  # keep unbound
            
            if password_form.is_valid():
                user = password_form.save()
                # Log the user out after successful password change
                logout(request)
                messages.success(request, 'Your password was changed successfully. Please log in again.')
                return redirect('core:client_login')
            else:
                messages.error(request, 'Please correct the errors in your password change form.')

    else:
        # GET request: initialize both forms
        profile_form = ClientProfileUpdateForm(instance=client_profile, user=user)
        password_form = ClientPasswordChangeForm(user)

    context = {
        'profile_form': profile_form,
        'password_form': password_form
    }

    return render(request, 'core/client_profile.html', context)


# --- CLIENT PUBLISHED FEED VIEW ---

@user_passes_test(is_client, login_url='core:client_login')
def client_feed_view(request):
    """
    Displays a paginated, Instagram-style feed of all the client's
    published posts.
    """
    client_profile = request.user.client_profile
    
    # Get all PUBLISHED posts for this client
    published_posts_query = Post.objects.filter(
        assigned_client=client_profile, 
        status=Post.Status.PUBLISHED
    ).annotate(
        avg_rating=Avg('ratings__score')
    ).order_by('-scheduled_datetime') # Newest first

    # Paginate the results (e.g., 9 posts per page for a 3x3 grid)
    paginator = Paginator(published_posts_query, 9) 
    page_number = request.GET.get('page')
    published_posts_page = paginator.get_page(page_number)

    context = {
        'published_posts': published_posts_page,
    }
    
    return render(request, 'core/client_feed.html', context)

# --- CLIENT POST REQUESTS LIST VIEW ---

@user_passes_test(is_client, login_url='core:client_login')
def client_pending_approval_view(request):
    """
    Displays a dedicated page for all posts pending client approval.
    """
    client_profile = request.user.client_profile
    
    # Get all posts for this client that are 'PENDING'
    pending_posts = Post.objects.filter(
        assigned_client=client_profile,
        status=Post.Status.PENDING
    ).order_by('scheduled_datetime')

    context = {
        'pending_posts': pending_posts,
    }
    
    return render(request, 'core/client_pending_approval.html', context)