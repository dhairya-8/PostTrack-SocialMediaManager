# posts/models.py

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import ClientProfile # Import from your new users app
from django.utils import timezone

class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'            
        PENDING = 'PENDING', 'Pending Approval' 
        APPROVED = 'APPROVED', 'Approved'      
        REJECTED = 'REJECTED', 'Rejected'      
        PUBLISHED = 'PUBLISHED', 'Published'    
        ARCHIVED = 'ARCHIVED', 'Archived'       

    title = models.CharField(max_length=255, help_text="Internal title for this post")
    caption = models.TextField(help_text="The social media post content")
    image = models.ImageField(upload_to='post_images/', help_text="Image for the post")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    scheduled_datetime = models.DateTimeField(null=True, blank=True, help_text="When the post is scheduled to go live")
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_posts',
        limit_choices_to={'role__in': ['ADMIN', 'SUPER_ADMIN']}
    )
    assigned_client = models.ForeignKey(
        ClientProfile, # Refers to the ClientProfile model in the users app
        on_delete=models.CASCADE,
        related_name='posts',
        help_text="Which client this post is for"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    created_from_request = models.ForeignKey(
        'PostRequest', # Links to the PostRequest model
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_posts',
        help_text="The client request this post was created from, if any."
    )

    def __str__(self):
        return f"{self.title} for {self.assigned_client.company_name} ({self.get_status_display()})"


class Feedback(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='feedback') # Refers to Post
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'CLIENT'}, 
    )
    comment = models.TextField(help_text="Client's suggestions or rejection reason")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback on {self.post.title} by {self.user.username}"


class Rating(models.Model):
    post = models.ForeignKey(
        Post, # Refers to Post
        on_delete=models.CASCADE,
        related_name='ratings',
        limit_choices_to={'status': Post.Status.PUBLISHED} 
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'CLIENT'},
    )
    score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], help_text="1-5 star rating")
    comment = models.TextField(blank=True, null=True, help_text="Optional comment with rating")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')

    def __str__(self):
        return f"{self.score}-star rating for {self.post.title}"


class PostVersion(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='versions') # Refers to Post
    caption_data = models.TextField(help_text="A snapshot of the caption")
    image_path = models.CharField(max_length=500, help_text="Path to the image file for this version")
    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp'] 

    def __str__(self):
        return f"Version of {self.post.title} from {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
class PostRequest(models.Model):
    """
    A model for clients to request a new post.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        VIEWED = 'VIEWED', 'Viewed by Admin'
        COMPLETED = 'COMPLETED', 'Completed'

    client = models.ForeignKey(
        ClientProfile, 
        on_delete=models.CASCADE, 
        related_name='post_requests'
    )
    desired_date = models.DateField(
        null=True, 
        blank=True, 
        help_text="Client's preferred date for the post"
    )
    request_details = models.TextField(
        help_text="Details and ideas for the post"
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Request from {self.client.company_name} (Status: {self.status})"