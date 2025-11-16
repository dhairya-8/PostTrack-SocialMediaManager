# reports/models.py

from django.db import models
from django.conf import settings

class GeneratedReport(models.Model):
    title = models.CharField(max_length=255)
    report_type = models.CharField(max_length=100, help_text="e.g., 'rejection_rates', 'engagement_trends'")
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='generated_reports/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.created_at.strftime('%Y-%m-%d')})"