# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render
from django.views.generic import TemplateView
from django.conf import settings
from .models import IntegrationConfiguration, IntegrationRun
from .serializers import IntegrationConfigurationSerializer, IntegrationRunSerializer
from .integration_processor import process_integration
from .pubsub_manager import (
    create_push_subscription,
    create_pull_subscription,
    delete_subscription,
    publish_test_message,
    handle_pubsub_push
)
from .pubsub_scheduler import get_scheduler
import time
import os
import json


class IntegrationConfigurationViewSet(viewsets.ModelViewSet):
    """API for managing integration configurations"""
    
    queryset = IntegrationConfiguration.objects.all()
    serializer_class = IntegrationConfigurationSerializer
    
    def create(self, request, *args, **kwargs):
        """Create new integration and start listeners if needed"""
        serializer = self.get_serializer(data=request.data)
        #serializer.is_valid(raise_exception=True)

        if not serializer.is_valid(raise_exception=False):
            # Validation failed, access the errors
            print(serializer.errors)
            print(request.data)
        else:
            print("Data is valid.")

        instance = serializer.save()
        
        # Start Pub/Sub listener if applicable
        if instance.source_type == 'pubsub' and instance.is_active:
            start_pubsub_listener(instance)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """Update integration - stop old listeners and start new ones"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Stop existing Pub/Sub listener if active
        if instance.source_type == 'pubsub' and instance.pubsub_listener_active:
            stop_pubsub_listener(instance)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if not serializer.is_valid(raise_exception=False):
            # Validation failed, access the errors
            print("UPDATE VALIDATION FAILED:")
            print(f"Errors: {serializer.errors}")
            print(f"Request data: {request.data}")
            print(f"Request content type: {request.content_type}")
        else:
            print("Update data is valid.")

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # Start new Pub/Sub listener if applicable
        if instance.source_type == 'pubsub' and instance.is_active:
            start_pubsub_listener(instance)
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Delete integration and stop listeners"""
        instance = self.get_object()
        
        # Stop Pub/Sub listener if active
        if instance.source_type == 'pubsub' and instance.pubsub_listener_active:
            stop_pubsub_listener(instance)
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle integration active status"""
        instance = self.get_object()
        instance.is_active = not instance.is_active
        instance.save()
        
        if instance.source_type == 'pubsub':
            if instance.is_active:
                start_pubsub_listener(instance)
            else:
                stop_pubsub_listener(instance)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def test_pubsub(self, request, pk=None):
        """Test Pub/Sub integration by publishing a test message"""
        instance = self.get_object()

        if instance.source_type != 'pubsub':
            return Response(
                {'error': 'Integration is not a Pub/Sub integration'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            message_data = request.data.get('message_data', {})
            config = instance.config_json
            source_config = config.get('sourceConfig', {})

            message_id = publish_test_message(
                project_id=instance.pubsub_project_id,
                topic_id=instance.pubsub_topic_id,
                message_data=message_data,
                credentials_json=source_config.get('credentials', '')
            )

            return Response({
                'status': 'success',
                'message': 'Test message published to Pub/Sub',
                'message_id': message_id,
                'topic': instance.pubsub_topic_id
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Pub/Sub management helper functions
def start_pubsub_listener(integration):
    """Create Pub/Sub subscription (push or pull) and start listener"""
    try:
        config = integration.config_json
        source_config = config.get('sourceConfig', {})
        credentials_json = source_config.get('credentials', '')

        if not credentials_json:
            print("No credentials provided for Pub/Sub")
            return

        subscription_mode = integration.pubsub_subscription_mode or 'push'

        if subscription_mode == 'push':
            # Build full push endpoint URL
            push_endpoint = f"{settings.SITE_URL}{integration.pubsub_push_endpoint}"

            create_push_subscription(
                project_id=integration.pubsub_project_id,
                topic_id=integration.pubsub_topic_id,
                subscription_id=integration.pubsub_subscription,
                push_endpoint=push_endpoint,
                credentials_json=credentials_json
            )
            print(f"Pub/Sub push subscription activated for {integration.name}")

        else:  # pull mode
            create_pull_subscription(
                project_id=integration.pubsub_project_id,
                topic_id=integration.pubsub_topic_id,
                subscription_id=integration.pubsub_subscription,
                credentials_json=credentials_json
            )

            # Start background puller
            scheduler = get_scheduler()
            scheduler.start_puller(integration)
            print(f"Pub/Sub pull subscription activated for {integration.name}")

        integration.pubsub_listener_active = True
        integration.save(update_fields=['pubsub_listener_active'])

    except Exception as e:
        print(f"Error starting Pub/Sub listener: {e}")
        raise


def stop_pubsub_listener(integration):
    """Delete Pub/Sub subscription and stop listener"""
    try:
        config = integration.config_json
        source_config = config.get('sourceConfig', {})
        credentials_json = source_config.get('credentials', '')

        if not credentials_json:
            print("No credentials provided for Pub/Sub")
            return

        subscription_mode = integration.pubsub_subscription_mode or 'push'

        # Stop pull scheduler if running
        if subscription_mode == 'pull':
            scheduler = get_scheduler()
            scheduler.stop_puller(str(integration.id))

        # Delete subscription
        delete_subscription(
            project_id=integration.pubsub_project_id,
            subscription_id=integration.pubsub_subscription,
            credentials_json=credentials_json
        )

        integration.pubsub_listener_active = False
        integration.save(update_fields=['pubsub_listener_active'])
        print(f"Pub/Sub subscription deactivated for {integration.name}")

    except Exception as e:
        print(f"Error stopping Pub/Sub listener: {e}")


class IntegrationRunViewSet(viewsets.ReadOnlyModelViewSet):
    """API for viewing integration run history"""
    
    queryset = IntegrationRun.objects.all()
    serializer_class = IntegrationRunSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        integration_id = self.request.query_params.get('integration_id')
        if integration_id:
            queryset = queryset.filter(integration_id=integration_id)
        return queryset


@csrf_exempt
@api_view(['POST'])
def webhook_handler(request, webhook_path):
    """Generic webhook handler that processes incoming webhook requests"""

    # Find integration by webhook path
    # Ensure trailing slash for consistency
    full_path = f"/webhook/{webhook_path}/"
    integration = get_object_or_404(
        IntegrationConfiguration,
        webhook_path=full_path,
        is_active=True,
        source_type='webhook'
    )

    # Process the webhook
    try:
        incoming_payload = request.data if hasattr(request, 'data') else json.loads(request.body)
        result = process_integration(integration, incoming_payload)

        return JsonResponse({
            'status': 'success',
            'run_id': str(result['run_id']),
            'message': 'Integration executed successfully'
        }, status=200)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@api_view(['POST'])
def pubsub_push_handler(request, push_path):
    """Handle push notifications from Google Pub/Sub"""

    # Find integration by push endpoint path
    full_path = f"/pubsub/{push_path}/"
    integration = get_object_or_404(
        IntegrationConfiguration,
        pubsub_push_endpoint=full_path,
        is_active=True,
        source_type='pubsub'
    )

    # Process the Pub/Sub push message
    try:
        request_body = request.data if hasattr(request, 'data') else json.loads(request.body)

        # Decode Pub/Sub message
        decoded_message = handle_pubsub_push(request_body)

        # Process through integration pipeline
        result = process_integration(integration, decoded_message['data'])

        # Return 204 No Content to acknowledge successful receipt
        # Pub/Sub considers 200-299 status codes as successful
        return JsonResponse({
            'status': 'success',
            'run_id': str(result['run_id']),
            'message_id': decoded_message['message_id']
        }, status=204)

    except Exception as e:
        print(f"Error processing Pub/Sub message: {e}")
        # Return error but still acknowledge receipt to prevent retries
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


def mapper_view(request):
    """Serve the mapper frontend"""
    frontend_path = os.path.join(settings.BASE_DIR.parent, 'frontend', 'index.html')

    if os.path.exists(frontend_path):
        with open(frontend_path, 'r') as f:
            content = f.read()
        from django.http import HttpResponse
        return HttpResponse(content, content_type='text/html')
    else:
        return JsonResponse({'error': 'Frontend not found'}, status=404)
