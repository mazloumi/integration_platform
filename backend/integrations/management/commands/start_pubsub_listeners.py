# management/commands/start_pubsub_listeners.py
# Django management command to start all active Pub/Sub listeners

from django.core.management.base import BaseCommand
from integrations.models import IntegrationConfiguration
from integrations.pubsub_listener import start_pubsub_listener


class Command(BaseCommand):
    help = 'Start all active Pub/Sub listeners'

    def handle(self, *args, **options):
        integrations = IntegrationConfiguration.objects.filter(
            source_type='pubsub',
            is_active=True
        )

        self.stdout.write(f"Found {integrations.count()} active Pub/Sub integrations")

        for integration in integrations:
            try:
                start_pubsub_listener(integration)
                self.stdout.write(
                    self.style.SUCCESS(f"Started listener for: {integration.name}")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to start listener for {integration.name}: {e}")
                )

