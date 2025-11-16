# users/models.py

from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        ADMIN = 'ADMIN', 'Admin'
        CLIENT = 'CLIENT', 'Client'

    role = models.CharField(max_length=50, choices=Role.choices)
    phone_number = models.CharField(max_length=20, blank=True, help_text="User's contact number")
    theme = models.CharField(max_length=10, default='light', choices=[('light', 'Light'), ('dark', 'Dark')], help_text="User's preferred theme")

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class ClientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={'role': 'CLIENT'}, # Enforces that only Clients can have this profile
        related_name='client_profile'
    )
    company_name = models.CharField(max_length=255, unique=True, help_text="The official name of the client's company")
    
    assigned_admins = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        limit_choices_to={'role': 'ADMIN'}, # Enforces that only Admins can be assigned
        related_name='assigned_clients', 
        blank=True
    )

    def __str__(self):
        return self.company_name