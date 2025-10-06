# apps.py
from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'integrations'

    def ready(self):
        """Start Pub/Sub listeners when Django starts"""
        # Only run in main process (not in reloader)
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            return
            
        from .models import IntegrationConfiguration
        from .pubsub_listener import start_pubsub_listener
        
        # Start all active Pub/Sub listeners
        try:
            integrations = IntegrationConfiguration.objects.filter(
                source_type='pubsub',
                is_active=True
            )
            
            for integration in integrations:
                try:
                    start_pubsub_listener(integration)
                    print(f"Started Pub/Sub listener for: {integration.name}")
                except Exception as e:
                    print(f"Failed to start listener for {integration.name}: {e}")
        except Exception as e:
            print(f"Error starting Pub/Sub listeners: {e}")
