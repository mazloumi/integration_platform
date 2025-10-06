# pubsub_scheduler.py
import threading
import time
from .pubsub_manager import pull_messages
from .integration_processor import process_integration


class PubSubPullScheduler:
    """
    Manages background threads for pulling messages from Pub/Sub subscriptions
    """

    def __init__(self):
        self.active_pullers = {}  # integration_id -> thread info
        self.lock = threading.Lock()

    def start_puller(self, integration):
        """
        Start a background thread to pull messages for an integration

        Args:
            integration: IntegrationConfiguration instance
        """
        integration_id = str(integration.id)

        with self.lock:
            # Stop existing puller if running
            if integration_id in self.active_pullers:
                self.stop_puller(integration_id)

            # Create stop event for this puller
            stop_event = threading.Event()

            # Start background thread
            thread = threading.Thread(
                target=self._pull_loop,
                args=(integration, stop_event),
                daemon=True
            )
            thread.start()

            self.active_pullers[integration_id] = {
                'thread': thread,
                'stop_event': stop_event,
                'integration': integration
            }

            print(f"Started pull scheduler for integration: {integration.name}")

    def stop_puller(self, integration_id):
        """
        Stop the background puller for an integration

        Args:
            integration_id: String ID of the integration
        """
        integration_id = str(integration_id)

        with self.lock:
            if integration_id in self.active_pullers:
                puller_info = self.active_pullers[integration_id]
                puller_info['stop_event'].set()

                # Wait for thread to finish (with timeout)
                puller_info['thread'].join(timeout=5.0)

                del self.active_pullers[integration_id]
                print(f"Stopped pull scheduler for integration: {integration_id}")

    def _pull_loop(self, integration, stop_event):
        """
        Background loop that pulls messages at regular intervals

        Args:
            integration: IntegrationConfiguration instance
            stop_event: Threading event to signal stop
        """
        config = integration.config_json
        source_config = config.get('sourceConfig', {})
        credentials_json = source_config.get('credentials', '')

        pull_interval = integration.pubsub_pull_interval_seconds or 60

        print(f"Pull loop started for {integration.name} (interval: {pull_interval}s)")

        while not stop_event.is_set():
            try:
                # Pull messages from subscription
                messages = pull_messages(
                    project_id=integration.pubsub_project_id,
                    subscription_id=integration.pubsub_subscription,
                    credentials_json=credentials_json,
                    max_messages=10
                )

                # Process each message through the integration
                for message in messages:
                    try:
                        result = process_integration(integration, message['data'])
                        print(f"Processed message {message['message_id']}: {result['status']}")
                    except Exception as e:
                        print(f"Error processing message {message['message_id']}: {e}")

            except Exception as e:
                print(f"Error in pull loop for {integration.name}: {e}")

            # Wait for interval or until stop signal
            stop_event.wait(timeout=pull_interval)

        print(f"Pull loop stopped for {integration.name}")

    def restart_puller(self, integration):
        """
        Restart a puller (stop and start)

        Args:
            integration: IntegrationConfiguration instance
        """
        integration_id = str(integration.id)
        self.stop_puller(integration_id)
        self.start_puller(integration)

    def is_running(self, integration_id):
        """
        Check if a puller is running for an integration

        Args:
            integration_id: String ID of the integration

        Returns:
            Boolean
        """
        integration_id = str(integration_id)
        with self.lock:
            return integration_id in self.active_pullers


# Global scheduler instance
_scheduler = None

def get_scheduler():
    """Get the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = PubSubPullScheduler()
    return _scheduler
