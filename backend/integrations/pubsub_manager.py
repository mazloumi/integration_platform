# pubsub_manager.py
import json
import base64
from google.cloud import pubsub_v1
from google.oauth2 import service_account
from django.conf import settings


def get_pubsub_credentials(credentials_json):
    """
    Parse service account credentials from JSON string
    """
    try:
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)
        return credentials
    except Exception as e:
        raise ValueError(f"Invalid service account credentials: {e}")


def create_push_subscription(project_id, topic_id, subscription_id, push_endpoint, credentials_json):
    """
    Create a push subscription to a Pub/Sub topic.

    Args:
        project_id: Google Cloud project ID
        topic_id: The Pub/Sub topic name
        subscription_id: Name for the subscription
        push_endpoint: HTTPS URL where messages will be pushed
        credentials_json: Service account JSON string

    Returns:
        Subscription object
    """
    credentials = get_pubsub_credentials(credentials_json)

    # Create subscriber client with credentials
    subscriber = pubsub_v1.SubscriberClient(credentials=credentials)

    # Build resource paths
    topic_path = subscriber.topic_path(project_id, topic_id)
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    # Configure push endpoint
    push_config = pubsub_v1.types.PushConfig(
        push_endpoint=push_endpoint
    )

    try:
        # Check if subscription already exists
        try:
            existing_sub = subscriber.get_subscription(request={"subscription": subscription_path})
            print(f"Subscription already exists: {existing_sub.name}")

            # Update push config if different
            if existing_sub.push_config.push_endpoint != push_endpoint:
                update_request = {
                    "subscription": {
                        "name": subscription_path,
                        "push_config": push_config
                    },
                    "update_mask": {"paths": ["push_config"]}
                }
                subscriber.update_subscription(request=update_request)
                print(f"Updated push endpoint to: {push_endpoint}")

            return existing_sub
        except Exception:
            # Subscription doesn't exist, create it
            subscription = subscriber.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                    "push_config": push_config,
                    "ack_deadline_seconds": 60
                }
            )
            print(f"Push subscription created: {subscription.name}")
            print(f"Messages will be pushed to: {push_endpoint}")
            return subscription

    except Exception as e:
        print(f"Error managing subscription: {e}")
        raise


def delete_subscription(project_id, subscription_id, credentials_json):
    """
    Delete a Pub/Sub subscription

    Args:
        project_id: Google Cloud project ID
        subscription_id: Name of the subscription to delete
        credentials_json: Service account JSON string
    """
    try:
        credentials = get_pubsub_credentials(credentials_json)
        subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
        subscription_path = subscriber.subscription_path(project_id, subscription_id)

        subscriber.delete_subscription(request={"subscription": subscription_path})
        print(f"Subscription deleted: {subscription_path}")
        return True
    except Exception as e:
        print(f"Error deleting subscription: {e}")
        return False


def publish_test_message(project_id, topic_id, message_data, credentials_json):
    """
    Publish a test message to a Pub/Sub topic

    Args:
        project_id: Google Cloud project ID
        topic_id: The Pub/Sub topic name
        message_data: Dictionary to publish
        credentials_json: Service account JSON string

    Returns:
        Message ID
    """
    credentials = get_pubsub_credentials(credentials_json)
    publisher = pubsub_v1.PublisherClient(credentials=credentials)
    topic_path = publisher.topic_path(project_id, topic_id)

    # Convert message data to JSON string and encode
    message_json = json.dumps(message_data)
    message_bytes = message_json.encode('utf-8')

    # Publish message
    future = publisher.publish(topic_path, message_bytes)
    message_id = future.result()

    print(f"Published message ID: {message_id}")
    return message_id


def create_pull_subscription(project_id, topic_id, subscription_id, credentials_json):
    """
    Create a pull subscription to a Pub/Sub topic.

    Args:
        project_id: Google Cloud project ID
        topic_id: The Pub/Sub topic name
        subscription_id: Name for the subscription
        credentials_json: Service account JSON string

    Returns:
        Subscription object
    """
    credentials = get_pubsub_credentials(credentials_json)

    # Create subscriber client with credentials
    subscriber = pubsub_v1.SubscriberClient(credentials=credentials)

    # Build resource paths
    topic_path = subscriber.topic_path(project_id, topic_id)
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    try:
        # Check if subscription already exists
        try:
            existing_sub = subscriber.get_subscription(request={"subscription": subscription_path})
            print(f"Pull subscription already exists: {existing_sub.name}")
            return existing_sub
        except Exception:
            # Subscription doesn't exist, create it
            subscription = subscriber.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": 60
                }
            )
            print(f"Pull subscription created: {subscription.name}")
            return subscription

    except Exception as e:
        print(f"Error managing pull subscription: {e}")
        raise


def pull_messages(project_id, subscription_id, credentials_json, max_messages=10):
    """
    Pull messages from a Pub/Sub subscription and acknowledge them.

    Args:
        project_id: Google Cloud project ID
        subscription_id: Name of the subscription
        credentials_json: Service account JSON string
        max_messages: Maximum number of messages to pull

    Returns:
        List of decoded message data
    """
    credentials = get_pubsub_credentials(credentials_json)
    subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    try:
        # Pull messages
        response = subscriber.pull(
            request={
                "subscription": subscription_path,
                "max_messages": max_messages,
            },
            timeout=10.0
        )

        messages = []
        ack_ids = []

        for received_message in response.received_messages:
            # Decode the message data
            message_data = received_message.message.data.decode('utf-8')

            # Parse JSON if message contains JSON
            try:
                data_json = json.loads(message_data)
            except json.JSONDecodeError:
                data_json = message_data

            messages.append({
                'message_id': received_message.message.message_id,
                'publish_time': received_message.message.publish_time,
                'data': data_json,
                'attributes': dict(received_message.message.attributes)
            })

            ack_ids.append(received_message.ack_id)

        # Acknowledge the messages
        if ack_ids:
            subscriber.acknowledge(
                request={
                    "subscription": subscription_path,
                    "ack_ids": ack_ids,
                }
            )
            print(f"Pulled and acknowledged {len(messages)} messages")

        return messages

    except Exception as e:
        print(f"Error pulling messages: {e}")
        return []


def handle_pubsub_push(request_body):
    """
    Process a push notification from Google Pub/Sub.
    Returns the decoded message data.

    Args:
        request_body: The JSON body from the HTTP POST request

    Returns:
        Dictionary with decoded message data
    """
    try:
        # Extract the message envelope
        if 'message' not in request_body:
            raise ValueError("Invalid Pub/Sub message format")

        message = request_body['message']

        # Decode the message data (base64 encoded)
        message_data = base64.b64decode(message['data']).decode('utf-8')

        # Get message attributes (metadata)
        attributes = message.get('attributes', {})

        # Get message ID and publish time
        message_id = message.get('messageId')
        publish_time = message.get('publishTime')

        # Parse JSON if message contains JSON
        try:
            data_json = json.loads(message_data)
        except json.JSONDecodeError:
            data_json = message_data

        return {
            'message_id': message_id,
            'publish_time': publish_time,
            'data': data_json,
            'attributes': attributes
        }

    except Exception as e:
        raise ValueError(f"Error processing Pub/Sub message: {e}")
