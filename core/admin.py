# users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import User, ClientProfile
from .models import Notification, AuditLog

class CustomUserAdmin(UserAdmin):
    """
    This customizes the admin panel to show your new 'role' field.
    """
    # This adds your custom fields to the user creation/edit form
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Profile', {'fields': ('role', 'phone_number', 'theme')}),
    )
    
    # This adds 'role' to the columns shown in the user list
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'role')

# Register your User model with the custom admin class
admin.site.register(User, CustomUserAdmin)

# Optionally, register your ClientProfile model too
admin.site.register(ClientProfile)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'message', 'is_read', 'timestamp')
    list_filter = ('is_read', 'timestamp')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'details')
    list_filter = ('action', 'user', 'timestamp')
    search_fields = ('user__username', 'details', 'action')