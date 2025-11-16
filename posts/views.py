# posts/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from .forms import PostCreationForm, PostEditForm, PostRequestForm, RatingForm
from .models import Post, Feedback, PostRequest
from users.models import User, ClientProfile
from django.utils import timezone

# --- Role Check Functions ---
def is_admin_or_superadmin(user):   
    return user.is_authenticated and user.role in [User.Role.ADMIN, User.Role.SUPER_ADMIN]

def is_client(user):
    return user.is_authenticated and user.role == User.Role.CLIENT

@user_passes_test(is_admin_or_superadmin, login_url='core:login_admin')
def create_post_view(request):
    """
    View for Admin/Super Admin to create a new post.
    Handles pre-filling from a PostRequest.
    """
    post_request = None
    client_profile = None
    initial_data = {}
    
    # --- 1. Handle GET request (Check for request_id) ---
    request_id = request.GET.get('request_id', None)
    if request_id:
        try:
            post_request = get_object_or_404(PostRequest, id=request_id)
            client_profile = post_request.client
            
            # --- FIX #1: Pre-fill all fields ---
            initial_data = {
                'title': f"Req: {post_request.request_details[:30]}...",
                'caption': post_request.request_details,
                'scheduled_datetime': post_request.desired_date,
                'assigned_client': client_profile # This pre-selects the client
            }
            
            # Security check
            if request.user.role == User.Role.ADMIN:
                if client_profile not in ClientProfile.objects.filter(assigned_admins=request.user):
                    messages.error(request, "You are not assigned to this client.")
                    return redirect('posts:admin_request_list')

            # --- FIX #2: Mark as "VIEWED" on GET (when you open the page) ---
            if post_request.status == PostRequest.Status.PENDING:
                post_request.status = PostRequest.Status.VIEWED
                post_request.save()
                
        except PostRequest.DoesNotExist:
            messages.error(request, "The post request could not be found.")
            return redirect('posts:admin_request_list')

    # --- 2. Handle POST request ---
    if request.method == 'POST':
        post_data = request.POST.copy()
        
        client_id = request.POST.get('client_id', None)
        if client_id and not post_data.get('assigned_client'):
            post_data['assigned_client'] = client_id
            
        form = PostCreationForm(post_data, request.FILES)
        
        if form.is_valid():
            post = form.save(commit=False)
            post.created_by = request.user
            post.status = Post.Status.DRAFT
            post.save() 
            
            post_request_id = request.POST.get('post_request_id', None)
            if post_request_id:
                try:
                    original_request = get_object_or_404(PostRequest, id=post_request_id)
                    
                    # --- FIX #3: Mark as "COMPLETED" on POST ---
                    original_request.status = PostRequest.Status.COMPLETED
                    original_request.save()
                    
                except PostRequest.DoesNotExist:
                    pass 
            
            messages.success(request, 'Post draft created successfully!')
            return redirect('posts:admin_request_list') # Redirect back to the list
        
        else:
            messages.error(request, 'Please correct the errors below.')
            # Re-fetch context if form is invalid
            if client_id:
                client_profile = get_object_or_404(ClientProfile, user_id=client_id)
            if request.POST.get('post_request_id'):
                post_request = get_object_or_404(PostRequest, id=request.POST.get('post_request_id'))

    else:
        # --- 4. On GET, pass initial_data to the form ---
        form = PostCreationForm(initial=initial_data)

    context = {
        'form': form,
        'post_request': post_request,
        'client_profile': client_profile
    }
    return render(request, 'posts/create_post.html', context)

@user_passes_test(is_client, login_url='core:client_login')
def client_review_post_view(request):
    """
    Handles the client's action (Approve/Reject) on a post.
    """
    if request.method != 'POST':
        return redirect('core:client_dashboard')

    post_id = request.POST.get('post_id')
    action = request.POST.get('action')
    comment_text = request.POST.get('comment', '').strip()

    try:
        post = Post.objects.get(id=post_id)
        
        if post.assigned_client != request.user.client_profile:
            messages.error(request, 'You do not have permission to review this post.')
            return redirect('core:client_dashboard')

        if action == 'approve':
            post.status = Post.Status.APPROVED
            post.save()
            
            # --- ✅ NEW LOGIC: UPDATE THE POST REQUEST ---
            # This is your Goal #2
            # Check if this post was created from a request using the new link
            if post.created_from_request:
                try:
                    # Get the original request
                    post_request = post.created_from_request
                    
                    # Update its status to COMPLETED
                    if post_request.status != PostRequest.Status.COMPLETED:
                        post_request.status = PostRequest.Status.COMPLETED
                        post_request.save()
                except PostRequest.DoesNotExist:
                    # The original request was somehow deleted, but the post is fine.
                    pass 
            # --- END OF NEW LOGIC ---

            messages.success(request, f'Post "{post.title}" has been approved.')
            
            if comment_text:
                Feedback.objects.create(post=post, user=request.user, comment=comment_text)

        elif action == 'reject':
            if not comment_text:
                messages.error(request, 'A comment is required when requesting changes.')
                # Go back to the page they were on
                return redirect(request.META.get('HTTP_REFERER', 'core:client_dashboard'))

            post.status = Post.Status.REJECTED
            post.save()
            
            Feedback.objects.create(post=post, user=request.user, comment=comment_text)
            messages.warning(request, f'Post "{post.title}" has been rejected with feedback.')
        
        else:
            messages.error(request, 'Invalid action.')

    except Post.DoesNotExist:
        messages.error(request, 'Post not found.')
    
    return redirect('core:client_dashboard')

@user_passes_test(is_admin_or_superadmin, login_url='core:login_admin')
def view_post_view(request, post_id):
    """
    Displays the full post details (for both Admin & Super Admin).
    Super Admins can only view, not edit.
    """
    from posts.models import Post, Feedback

    post = get_object_or_404(Post, id=post_id)
    feedbacks = post.feedback.all().order_by('-created_at')

    # Check if admin is allowed to see this post
    if request.user.role == User.Role.ADMIN:
        admin_clients = ClientProfile.objects.filter(assigned_admins=request.user)
        if post.assigned_client not in admin_clients:
            messages.error(request, "You are not authorized to view this post.")
            return redirect('posts:post_list')

    context = {
        'post': post,
        'feedbacks': feedbacks,
    }
    return render(request, 'posts/post_detail.html', context)

@user_passes_test(is_admin_or_superadmin, login_url='core:login_admin')
def edit_post_view(request, post_id):
    """
    View for Admin/Super Admin to edit a post and resubmit it.
    """
    post = get_object_or_404(Post, id=post_id)

    if request.user.role == User.Role.ADMIN:
        admin_clients = ClientProfile.objects.filter(assigned_admins=request.user)
        if post.assigned_client not in admin_clients:
            messages.error(request, "You do not have permission to edit this post.")
            return redirect('core:dashboard')

    if request.method == 'POST':
        form = PostEditForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            edited_post = form.save(commit=False)
            edited_post.status = Post.Status.PENDING
            edited_post.save()
            messages.success(request, f'Post "{edited_post.title}" has been updated and resubmitted for approval.')
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PostEditForm(instance=post)

    feedback_history = post.feedback.all().order_by('-created_at')

    context = {
        'form': form,
        'post': post,
        'feedback_history': feedback_history
    }
    return render(request, 'posts/edit_post.html', context)

@user_passes_test(is_admin_or_superadmin, login_url='core:login_admin')
def mark_post_pending_view(request, post_id):
    """
    Allows Admin or Super Admin to mark a draft post as ready (PENDING).
    """
    post = get_object_or_404(Post, id=post_id)

    # ✅ Permission check (only assigned admin or super_admin)
    if request.user.role == User.Role.ADMIN:
        admin_clients = ClientProfile.objects.filter(assigned_admins=request.user)
        if post.assigned_client not in admin_clients:
            messages.error(request, "You do not have permission to modify this post.")
            return redirect('posts:post_list')

    if post.status == Post.Status.DRAFT:
        post.status = Post.Status.PENDING
        post.save()
        messages.success(request, f'Post "{post.title}" is now marked as ready for client review.')
    else:
        messages.info(request, 'Only draft posts can be marked as pending.')

    return redirect('posts:post_list')

@user_passes_test(is_admin_or_superadmin, login_url='core:login_admin')
def delete_post_view(request, post_id):
    """
    Allows Admin/SuperAdmin to delete a post.
    """
    post = get_object_or_404(Post, id=post_id)

    if request.user.role == User.Role.ADMIN:
        allowed_clients = ClientProfile.objects.filter(assigned_admins=request.user)
        if post.assigned_client not in allowed_clients:
            messages.error(request, "You don't have permission to delete this post.")
            return redirect('posts:post_list')

    if request.method == 'POST':
        post_title = post.title
        post.delete()
        messages.success(request, f'Post "{post_title}" has been deleted successfully.')
        return redirect('posts:post_list')
    
    # fallback (GET access) – just redirect to list
    return redirect('posts:post_list')


@user_passes_test(is_admin_or_superadmin, login_url='core:login_admin')
def post_list_view(request):
    """
    Displays a list of all posts, filterable by status.
    """
    Post.objects.filter(status=Post.Status.APPROVED, scheduled_datetime__lte=timezone.now()).update(status=Post.Status.PUBLISHED)

    user = request.user
    
    status_filter = request.GET.get('status', 'ALL')

    if user.role == User.Role.SUPER_ADMIN:
        base_queryset = Post.objects.all()
    else:
        admin_clients = ClientProfile.objects.filter(assigned_admins=user)
        base_queryset = Post.objects.filter(assigned_client__in=admin_clients)

    if status_filter == 'ALL' or not status_filter:
        filtered_posts = base_queryset.all()
    else:
        filtered_posts = base_queryset.filter(status=status_filter)
        
    filtered_posts = filtered_posts.order_by('-updated_at')
    
    status_counts = {
        'ALL': base_queryset.count(),
        'DRAFT': base_queryset.filter(status=Post.Status.DRAFT).count(),
        'PENDING': base_queryset.filter(status=Post.Status.PENDING).count(),
        'APPROVED': base_queryset.filter(status=Post.Status.APPROVED).count(),
        'REJECTED': base_queryset.filter(status=Post.Status.REJECTED).count(),
        'PUBLISHED': base_queryset.filter(status=Post.Status.PUBLISHED).count(),
    }

    context = {
        'posts': filtered_posts,
        'status_counts': status_counts,
        'current_status': status_filter,
    }
    
    return render(request, 'posts/post_list.html', context)

@user_passes_test(is_admin_or_superadmin, login_url='core:login_admin')
def admin_post_request_list_view(request):
    """
    Displays a list of all client post requests for admins.
    Includes filtering by status and respects Admin/SuperAdmin roles.
    """
    user = request.user
    status_filter = request.GET.get('status', 'ALL')

    # 1. --- Role-Based Base Queryset (Mirrors your logic) ---
    if user.role == User.Role.SUPER_ADMIN:
        # SuperAdmin sees all requests
        base_queryset = PostRequest.objects.all()
    else:
        # Admin only sees requests from their assigned clients
        try:
            admin_clients = ClientProfile.objects.filter(assigned_admins=user)
            base_queryset = PostRequest.objects.filter(client__in=admin_clients)
        except ClientProfile.DoesNotExist:
            base_queryset = PostRequest.objects.none()

    # 2. --- Apply Status Filter (Mirrors your logic) ---
    if status_filter == 'ALL' or not status_filter:
        filtered_requests = base_queryset.all()
    else:
        # Ensure the status is valid before filtering
        valid_statuses = [PostRequest.Status.PENDING, PostRequest.Status.VIEWED, PostRequest.Status.COMPLETED]
        if status_filter in valid_statuses:
            filtered_requests = base_queryset.filter(status=status_filter)
        else:
            filtered_requests = base_queryset.all() # Default to all if filter is invalid
            
    # Order by most recent
    filtered_requests = filtered_requests.order_by('-created_at')
    
    # 3. --- Get Status Counts (Mirrors your logic) ---
    # Counts are based on the user's base_queryset (SuperAdmin sees all, Admin sees theirs)
    status_counts = {
        'ALL': base_queryset.count(),
        'PENDING': base_queryset.filter(status=PostRequest.Status.PENDING).count(),
        'VIEWED': base_queryset.filter(status=PostRequest.Status.VIEWED).count(),
        'COMPLETED': base_queryset.filter(status=PostRequest.Status.COMPLETED).count(),
    }

    # 4. --- Prepare Context (Mirrors your logic) ---
    context = {
        'requests': filtered_requests,
        'status_counts': status_counts,
        'current_status': status_filter,
    }
    
    return render(request, 'posts/admin_request_list.html', context)


# --- CLIENT POST REQUEST VIEW ---

@user_passes_test(is_client, login_url='core:client_login')
def request_post_view(request):
    """
    Handles the client's form for requesting a new post
    AND displays their list of existing requests.
    """
    
    # --- Fetch existing requests (Needed for both GET and POST) ---
    try:
        # Get the client profile associated with the logged-in user
        client_profile = request.user.client_profile
        # Fetch all requests for this client, most recent first
        existing_requests = PostRequest.objects.filter(client=client_profile).order_by('-created_at')
    except ClientProfile.DoesNotExist:
        messages.error(request, 'Your client profile could not be found.')
        existing_requests = PostRequest.objects.none() # Return an empty list
        client_profile = None # Ensure client_profile is defined

    # --- Handle Form Submission ---
    if request.method == 'POST':
        form = PostRequestForm(request.POST)
        if form.is_valid() and client_profile:
            post_request = form.save(commit=False)
            post_request.client = client_profile # Assign the client
            post_request.save()
            
            messages.success(request, 'Your post request has been submitted!')
            
            # --- IMPORTANT ---
            # Redirect back to this SAME page. 
            # This is better UX as they will see their new request in the table.
            # Replace 'posts:request_post' with the actual name from your urls.py
            return redirect('posts:request_post') 
    else:
        # --- On GET, create a blank form ---
        form = PostRequestForm()
    
    # --- Prepare context for rendering ---
    context = {
        'form': form,
        'existing_requests': existing_requests
    }
    
    # Render the same template
    return render(request, 'posts/request_post.html', context)

# --- NEW: CLIENT POST DETAIL & RATING VIEW ---

@user_passes_test(is_client, login_url='core:client_login')
def client_post_detail_view(request, post_id):
    """
    Displays a single published post for rating and viewing comments.
    """
    # 1. Get the post, ensuring it belongs to this client
    post = get_object_or_404(
        Post, 
        id=post_id, 
        assigned_client=request.user.client_profile
    )
    
    # 2. Get all existing ratings/comments for this post
    all_ratings = post.ratings.all().order_by('-created_at')
    
    # 3. Check if this client has already rated this post
    user_rating = post.ratings.filter(user=request.user).first()
    
    if request.method == 'POST':
        # 4. Handle form submission
        if not user_rating and post.status == Post.Status.PUBLISHED:
            form = RatingForm(request.POST)
            if form.is_valid():
                new_rating = form.save(commit=False)
                new_rating.post = post
                new_rating.user = request.user
                new_rating.save()
                messages.success(request, 'Thank you for your rating!')
                return redirect('posts:client_post_detail', post_id=post.id)
        else:
            # Prevent re-submission
            messages.error(request, 'You have already rated this post.')
            return redirect('posts:client_post_detail', post_id=post.id)
            
    else:
        # 5. On GET request, show an empty form
        form = RatingForm()

    context = {
        'post': post,
        'ratings': all_ratings,
        'rating_form': form,
        'user_rating': user_rating, # This will be None or a Rating object
    }
    
    return render(request, 'posts/client_post_detail.html', context)