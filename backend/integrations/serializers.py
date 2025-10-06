# serializers.py
import uuid
from rest_framework import serializers
from .models import IntegrationConfiguration, IntegrationRun

class IntegrationConfigurationSerializer(serializers.ModelSerializer):
    webhook_url = serializers.SerializerMethodField()
    
    class Meta:
        model = IntegrationConfiguration
        fields = [
            'id', 'name', 'config_json', 'source_type', 'webhook_path',
            'webhook_url', 'target_url', 'target_method', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'webhook_path']
        extra_kwargs = {
            'source_type': {'required': False, 'allow_null': True, 'allow_blank': True},
            'target_url': {'required': False, 'allow_null': True, 'allow_blank': True},
            'target_method': {'required': False, 'allow_null': True, 'allow_blank': True},
        }
    
    def get_webhook_url(self, obj):
        return obj.get_webhook_url()
    
    def create(self, validated_data):
        config = validated_data['config_json']
        
        # Extract fields from config
        validated_data['source_type'] = config.get('sourceType', 'webhook')
        validated_data['target_url'] = config.get('target', {}).get('url', '')
        validated_data['target_method'] = config.get('target', {}).get('method', 'POST')
        
        # Generate webhook path if source is webhook
        if validated_data['source_type'] == 'webhook':
            validated_data['webhook_path'] = f"/webhook/{uuid.uuid4().hex[:16]}/"
        
        # Extract Pub/Sub config if applicable
        if validated_data['source_type'] == 'pubsub':
            source_config = config.get('sourceConfig', {})
            validated_data['pubsub_project_id'] = source_config.get('projectId')
            validated_data['pubsub_topic_id'] = source_config.get('topicId')
            validated_data['pubsub_subscription'] = source_config.get('subscription')
            validated_data['pubsub_subscription_mode'] = source_config.get('subscriptionMode', 'push')
            validated_data['pubsub_pull_interval_seconds'] = source_config.get('pullIntervalSeconds', 60)
            # Generate push endpoint path only for push mode
            if validated_data['pubsub_subscription_mode'] == 'push':
                validated_data['pubsub_push_endpoint'] = f"/pubsub/{uuid.uuid4().hex[:16]}/"

        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        config = validated_data.get('config_json', instance.config_json)
        
        # Update extracted fields
        validated_data['source_type'] = config.get('sourceType', instance.source_type)
        validated_data['target_url'] = config.get('target', {}).get('url', instance.target_url)
        validated_data['target_method'] = config.get('target', {}).get('method', instance.target_method)
        
        # Update Pub/Sub config if applicable
        if validated_data['source_type'] == 'pubsub':
            source_config = config.get('sourceConfig', {})
            validated_data['pubsub_project_id'] = source_config.get('projectId')
            validated_data['pubsub_topic_id'] = source_config.get('topicId')
            validated_data['pubsub_subscription'] = source_config.get('subscription')
            validated_data['pubsub_subscription_mode'] = source_config.get('subscriptionMode', 'push')
            validated_data['pubsub_pull_interval_seconds'] = source_config.get('pullIntervalSeconds', 60)
            # Keep existing push endpoint if it exists, otherwise generate new one (push mode only)
            if validated_data['pubsub_subscription_mode'] == 'push' and not instance.pubsub_push_endpoint:
                validated_data['pubsub_push_endpoint'] = f"/pubsub/{uuid.uuid4().hex[:16]}/"

        return super().update(instance, validated_data)


class IntegrationRunSerializer(serializers.ModelSerializer):
    integration_name = serializers.CharField(source='integration.name', read_only=True)
    
    class Meta:
        model = IntegrationRun
        fields = [
            'id', 'integration', 'integration_name', 'incoming_payload',
            'transformed_payload', 'outgoing_request', 'outgoing_response',
            'status', 'error_message', 'transformation_time_ms',
            'api_call_time_ms', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

