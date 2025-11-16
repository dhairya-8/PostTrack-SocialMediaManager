# core/models.py

from django.db import models
from django.conf import settings
from posts.models import Post # Import from your new posts app

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    related_post = models.ForeignKey(Post, on_delete=models.SET_NULL, null=True, blank=True) # Refers to Post
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message[:30]}..."


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100, help_text="e.g., 'user_login', 'post_edit', 'client_assigned'")
    details = models.TextField(blank=True, null=True, help_text="Extra info, e.g., IP address or object ID")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {user_str}: {self.action}"