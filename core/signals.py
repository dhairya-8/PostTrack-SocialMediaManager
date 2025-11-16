# core/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from posts.models import Post, Feedback, Rating
from .models import Notification, AuditLog
from django.contrib.auth.signals import user_logged_in

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Create an AuditLog entry when a user logs in.
    """
    AuditLog.objects.create(
        user=user,
        action="user_login",
        details=f"User {user.username} logged in."
    )

@receiver(post_save, sender=Post)
def post_save_receiver(sender, instance, created, **kwargs):
    """
    Create Notifications and AuditLog entries for Post updates.
    """
    post = instance
    
    # --- Audit Log Logic ---
    if created:
        AuditLog.objects.create(
            user=post.created_by,
            action="post_create",
            details=f"Admin {post.created_by.username} created post '{post.title}'."
        )
    else:
        AuditLog.objects.create(
            user=instance.created_by,
            action="post_edit",
            details=f"Post '{post.title}' was updated. New status: {post.get_status_display()}."
        )

    # --- Notification Logic ---
    
    # Notify ADMIN when REJECTED
    if post.status == Post.Status.REJECTED and post.created_by:
        message = f"Client rejected post: '{post.title[:30]}...'"
        Notification.objects.create(recipient=post.created_by, message=message, related_post=post)
    
    # Notify ADMIN when APPROVED
    if post.status == Post.Status.APPROVED and post.created_by:
        message = f"Client approved post: '{post.title[:30]}...'"
        Notification.objects.create(recipient=post.created_by, message=message, related_post=post)

    # Notify CLIENT when PENDING
    if post.status == Post.Status.PENDING:
        client_user = post.assigned_client.user
        message = f"New post ready for review: '{post.title[:30]}...'"
        Notification.objects.create(recipient=client_user, message=message, related_post=post)
        
    # === NEW: Notify CLIENT when PUBLISHED ===
    if post.status == Post.Status.PUBLISHED:
        # Check if it was *just* published (we don't want to notify every time it's saved)
        if kwargs.get('update_fields') and 'status' in kwargs['update_fields']:
            client_user = post.assigned_client.user
            message = f"Your post '{post.title[:30]}...' has been published!"
            Notification.objects.create(recipient=client_user, message=message, related_post=post)

@receiver(post_save, sender=Feedback)
def create_feedback_notification_and_log(sender, instance, created, **kwargs):
    if created:
        admin_user = instance.post.created_by
        
        AuditLog.objects.create(
            user=instance.user,
            action="post_feedback",
            details=f"Client {instance.user.username} left feedback on '{instance.post.title}'."
        )
        
        # Notify ADMIN (but not if it was part of a rejection)
        if admin_user and instance.post.status != Post.Status.REJECTED:
            message = f"Client left feedback on '{instance.post.title[:30]}...'"
            Notification.objects.create(recipient=admin_user, message=message, related_post=instance.post)

@receiver(post_save, sender=Rating)
def create_rating_notification_and_log(sender, instance, created, **kwargs):
    if created:
        admin_user = instance.post.created_by
        
        AuditLog.objects.create(
            user=instance.user,
            action="post_rating",
            details=f"Client {instance.user.username} rated '{instance.post.title}' {instance.score} stars."
        )
        
        # Notify ADMIN
        if admin_user:
            message = f"Client rated '{instance.post.title[:30]}...' {instance.score} stars."
            Notification.objects.create(recipient=admin_user, message=message, related_post=instance.post)