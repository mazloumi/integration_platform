# admin.py
import json
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import IntegrationConfiguration, IntegrationRun


@admin.register(IntegrationConfiguration)
class IntegrationConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'target_method', 'target_url', 'is_active', 'created_at', 'frontend_link']
    list_filter = ['source_type', 'target_method', 'is_active', 'created_at']
    search_fields = ['name', 'target_url', 'webhook_path']
    readonly_fields = ['id', 'webhook_path', 'created_at', 'updated_at', 'webhook_url_display']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['id', 'name', 'is_active']
        }),
        ('Configuration', {
            'fields': ['config_json']
        }),
        ('Source', {
            'fields': ['source_type', 'webhook_path', 'webhook_url_display', 
                      'pubsub_project_id', 'pubsub_subscription', 'pubsub_listener_active']
        }),
        ('Target', {
            'fields': ['target_url', 'target_method']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at']
        }),
    ]
    
    def webhook_url_display(self, obj):
        if obj.webhook_path:
            url = obj.get_webhook_url()
            return format_html('<code>{}</code>', url)
        return '-'
    webhook_url_display.short_description = 'Webhook URL'
    
    def frontend_link(self, obj):
        # URL to your frontend with integration ID
        url = f"http://localhost:3000?integration_id={obj.id}"
        return format_html('<a href="{}" target="_blank">Open Editor</a>', url)
    frontend_link.short_description = 'Frontend'


@admin.register(IntegrationRun)
class IntegrationRunAdmin(admin.ModelAdmin):
    list_display = ['integration', 'status', 'created_at', 'transformation_time_ms', 'api_call_time_ms']
    list_filter = ['status', 'created_at', 'integration']
    search_fields = ['integration__name', 'error_message']
    readonly_fields = [
        'id', 'integration', 'condition_display', 'incoming_payload_display', 'transformed_payload_display',
        'outgoing_request_display', 'outgoing_response_display', 'status',
        'error_message', 'transformation_time_ms', 'api_call_time_ms', 'created_at'
    ]

    fieldsets = [
        ('Run Information', {
            'fields': ['id', 'integration', 'status', 'created_at']
        }),
        ('Condition Evaluation', {
            'fields': ['condition_display']
        }),
        ('Incoming Data', {
            'fields': ['incoming_payload_display']
        }),
        ('Transformation', {
            'fields': ['transformed_payload_display', 'transformation_time_ms']
        }),
        ('Outgoing Request', {
            'fields': ['outgoing_request_display', 'api_call_time_ms']
        }),
        ('Response', {
            'fields': ['outgoing_response_display']
        }),
        ('Errors', {
            'fields': ['error_message']
        }),
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

    def condition_display(self, obj):
        request_data = obj.outgoing_request or {}
        condition = request_data.get('condition')
        condition_result = request_data.get('condition_result')

        if condition:
            result_color = '#28a745' if condition_result else '#dc3545'
            result_text = 'TRUE ✅' if condition_result else 'FALSE ❌'
            return format_html(
                '<div style="margin-bottom: 10px;"><strong>Result:</strong> <span style="color: {}; font-weight: bold;">{}</span></div>'
                '<div><strong>Condition Code:</strong></div>'
                '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>',
                result_color, result_text, condition
            )
        else:
            return format_html('<div style="color: #666;">No condition defined (always executes)</div>')
    condition_display.short_description = 'Condition Evaluation'

    def incoming_payload_display(self, obj):
        return format_html('<pre>{}</pre>', json.dumps(obj.incoming_payload, indent=2))
    incoming_payload_display.short_description = 'Incoming Payload'
    
    def transformed_payload_display(self, obj):
        return format_html('<pre>{}</pre>', json.dumps(obj.transformed_payload, indent=2))
    transformed_payload_display.short_description = 'Transformed Payload'
    
    def outgoing_request_display(self, obj):
        return format_html('<pre>{}</pre>', json.dumps(obj.outgoing_request, indent=2))
    outgoing_request_display.short_description = 'Outgoing Request'
    
    def outgoing_response_display(self, obj):
        return format_html('<pre>{}</pre>', json.dumps(obj.outgoing_response, indent=2))
    outgoing_response_display.short_description = 'Outgoing Response'

