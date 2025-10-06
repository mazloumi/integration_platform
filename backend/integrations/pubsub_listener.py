# pubsub_listener.py
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError
import threading

# Store active subscribers
_active_subscribers = {}


def start_pubsub_listener(integration: IntegrationConfiguration):
    """Start a Pub/Sub listener for an integration"""
    
    if integration.id in _active_subscribers:
        print(f"Listener already active for {integration.name}")
        return
    
    project_id = integration.pubsub_project_id
    subscription_name = integration.pubsub_subscription
    
    if not project_id or not subscription_name:
        print(f"Missing Pub/Sub configuration for {integration.name}")
        return
    
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)
    
    def callback(message):
        """Process incoming Pub/Sub message"""
        try:
            payload = json.loads(message.data.decode('utf-8'))
            process_integration(integration, payload)
            message.ack()
        except Exception as e:
            print(f"Error processing Pub/Sub message: {e}")
            message.nack()
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    
    # Store subscriber info
    _active_subscribers[integration.id] = {
        'subscriber': subscriber,
        'future': streaming_pull_future,
        'thread': threading.current_thread()
    }
    
    integration.pubsub_listener_active = True
    integration.save()
    
    print(f"Started Pub/Sub listener for {integration.name} on {subscription_path}")


def stop_pubsub_listener(integration: IntegrationConfiguration):
    """Stop a Pub/Sub listener"""
    
    if integration.id not in _active_subscribers:
        print(f"No active listener for {integration.name}")
        return
    
    subscriber_info = _active_subscribers[integration.id]
    streaming_pull_future = subscriber_info['future']
    
    streaming_pull_future.cancel()
    
    del _active_subscribers[integration.id]
    
    integration.pubsub_listener_active = False
    integration.save()
    
    print(f"Stopped Pub/Sub listener for {integration.name}")

