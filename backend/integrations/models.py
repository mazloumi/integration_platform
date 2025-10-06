# models.py
from django.db import models
from django.utils import timezone
import json
import uuid


class IntegrationConfiguration(models.Model):
    """Stores JSON integration definitions"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    
    # Store entire integration config as JSON
    config_json = models.JSONField(help_text="Complete integration configuration")
    
    # Extracted fields for easier querying
    source_type = models.CharField(
        max_length=50,
        choices=[('webhook', 'Webhook'), ('pubsub', 'Google Pub/Sub')],
        db_index=True
    )
    webhook_path = models.CharField(
        max_length=255, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="Unique webhook path (e.g., /webhook/abc123)"
    )
    target_url = models.URLField(max_length=500)
    target_method = models.CharField(max_length=10, choices=[('GET', 'GET'), ('POST', 'POST')])
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Pub/Sub configuration
    pubsub_project_id = models.CharField(max_length=255, null=True, blank=True)
    pubsub_topic_id = models.CharField(max_length=255, null=True, blank=True)
    pubsub_subscription = models.CharField(max_length=255, null=True, blank=True)
    pubsub_subscription_mode = models.CharField(
        max_length=10,
        choices=[('push', 'Push'), ('pull', 'Pull')],
        default='push',
        null=True,
        blank=True
    )
    pubsub_push_endpoint = models.CharField(max_length=500, null=True, blank=True)
    pubsub_pull_interval_seconds = models.IntegerField(
        default=60,
        null=True,
        blank=True,
        help_text="Interval in seconds for pulling messages (pull mode only)"
    )
    pubsub_listener_active = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Integration Configuration"
        verbose_name_plural = "Integration Configurations"
    
    def __str__(self):
        return f"{self.name} ({self.source_type})"
    
    def get_webhook_url(self):
        """Returns full webhook URL"""
        from django.conf import settings
        if self.webhook_path:
            site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            return f"{site_url}{self.webhook_path}"
        return None


class IntegrationRun(models.Model):
    """Logs each integration execution"""
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('skipped', 'Skipped'),
        ('error', 'Error'),
        ('partial', 'Partial Success'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.ForeignKey(
        IntegrationConfiguration,
        on_delete=models.CASCADE,
        related_name='runs'
    )
    
    # Request/Response data
    incoming_payload = models.JSONField(help_text="Payload received from source")
    transformed_payload = models.JSONField(help_text="Payload after transformation")
    outgoing_request = models.JSONField(help_text="Complete request sent to target API")
    outgoing_response = models.JSONField(help_text="Response from target API")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, db_index=True)
    error_message = models.TextField(null=True, blank=True)
    
    # Performance metrics
    transformation_time_ms = models.IntegerField(null=True, help_text="Time to transform data")
    api_call_time_ms = models.IntegerField(null=True, help_text="Time for API call")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Integration Run"
        verbose_name_plural = "Integration Runs"
        indexes = [
            models.Index(fields=['-created_at', 'status']),
            models.Index(fields=['integration', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.integration.name} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {self.status}"
