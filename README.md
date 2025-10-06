# JSON Mapper Integration Platform

A Django-based platform for visual JSON mapping with webhook and Google Cloud Pub/Sub integration.

## Features

### Source Types
- **Webhooks**: Auto-generated unique webhook URLs for receiving HTTP POST requests
- **Google Cloud Pub/Sub**:
  - **Push Mode**: Google automatically sends messages to your endpoint
  - **Pull Mode**: Background scheduler polls for messages at configurable intervals

### Target Types
- **HTTP/HTTPS**: Send transformed data to any REST API endpoint
  - Support for GET and POST methods
  - Multiple authentication types (Bearer, Basic Auth, API Key)
  - Custom headers support
- **Email (SMTP)**: Send transformed data via email
  - Configurable SMTP server and credentials
  - Support for TLS/SSL
  - Dynamic recipient and subject fields

### Transformations & Mapping
- **Visual JSON Mapper**: Interactive interface for mapping source fields to target fields
- **Built-in Transformations**: uppercase, lowercase, substring, replace, default, concat
- **Custom JavaScript**: Write custom transformation logic using JavaScript
- **Conditional Processing**: JavaScript-based conditions to skip or process integrations

### Management & Monitoring
- **Complete Audit Trail**: Log every integration execution with full request/response data
- **Performance Metrics**: Track transformation time and API call time
- **Django Admin Interface**: Manage integrations and view logs
- **Change Tracking**: Frontend validation before saving changes
- **Active/Inactive Toggle**: Enable or disable integrations without deleting

## Installation

1. Clone the repository
2. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` and set `SITE_URL` to your domain (important for webhooks and Pub/Sub):
   ```bash
   # For local development
   SITE_URL=http://localhost:8000

   # For production
   SITE_URL=https://integrations.yourdomain.com
   ```
4. Install dependencies: `pip install -r requirements.txt`
5. Run migrations: `python manage.py migrate`
6. Create superuser: `python manage.py createsuperuser`
7. Start server: `python manage.py runserver`

## Usage

### Creating an Integration

1. Navigate to `https://yourdomain:8000/admin/` in your browser
2. Configure source (Webhook or Pub/Sub)
3. Configure target API endpoint
4. Map fields from source to target
5. Save to backend

### Webhook Integration

When you save a webhook integration, a unique URL is generated:
```
https://yourdomain.com/webhook/abc123/
```

Send POST requests to this URL with JSON payload. The integration will:
1. Receive the payload
2. Apply any conditional logic
3. Transform data according to field mappings
4. Send to the configured target (HTTP/Email)
5. Log the complete execution

### Pub/Sub Integration

#### Push Mode
For Pub/Sub push integrations:
1. Configure GCP Project ID, Topic Name, and Subscription Name
2. Paste service account JSON credentials
3. Select "Push" mode
4. Save integration - a push endpoint is auto-generated
5. Google Pub/Sub automatically sends messages to your endpoint

Example push endpoint: `https://yourdomain.com/pubsub/xyz789/`

#### Pull Mode
For Pub/Sub pull integrations:
1. Configure GCP Project ID, Topic Name, and Subscription Name
2. Paste service account JSON credentials
3. Select "Pull" mode
4. Set pull interval in seconds (default: 60)
5. Save integration - a background thread starts polling for messages

The pull scheduler will:
- Check for new messages at the specified interval
- Process messages through the integration pipeline
- Automatically acknowledge processed messages
- Handle errors without losing messages

### Email Target Integration

Configure SMTP settings to send transformed data via email:
```json
{
  "smtpServer": "smtp.gmail.com",
  "smtpPort": 587,
  "smtpUsername": "your-email@gmail.com",
  "smtpPassword": "your-app-password",
  "fromEmail": "sender@example.com",
  "toEmail": "recipient@example.com",
  "subject": "Integration Alert",
  "useTLS": true
}
```

### Viewing Logs

1. Go to Django Admin: `/admin/`
2. View "Integration Runs" to see all executions
3. Click on any run to see incoming/outgoing payloads and responses

## API Endpoints

### Integration Management
- `POST /api/integrations/` - Create integration
- `GET /api/integrations/` - List integrations
- `GET /api/integrations/{id}/` - Get integration
- `PUT /api/integrations/{id}/` - Update integration
- `DELETE /api/integrations/{id}/` - Delete integration
- `POST /api/integrations/{id}/toggle_active/` - Toggle active status
- `POST /api/integrations/{id}/test_pubsub/` - Test Pub/Sub integration by publishing a message

### Integration Runs
- `GET /api/runs/` - List integration runs
- `GET /api/runs/?integration_id={id}` - Filter runs by integration
- `GET /api/runs/{id}/` - Get run details

### Webhook & Pub/Sub Handlers
- `POST /webhook/{path}/` - Webhook endpoint (auto-generated per integration)
- `POST /pubsub/{path}/` - Pub/Sub push endpoint (auto-generated per integration)

## Architecture

### Models

**IntegrationConfiguration**
- Stores complete integration definition as JSON (config_json field)
- Extracts key fields for querying: source_type, target_url, target_method
- Generates unique webhook paths and Pub/Sub push endpoints
- Tracks Pub/Sub configuration:
  - project_id, topic_id, subscription
  - subscription_mode (push/pull)
  - pull_interval_seconds
  - listener_active status
- Links to IntegrationRun records for audit trail

**IntegrationRun**
- Logs every integration execution
- Stores:
  - incoming_payload: Original data from source
  - transformed_payload: Data after mappings and transformations
  - outgoing_request: Full request sent to target (headers, body, URL)
  - outgoing_response: Response from target
  - status: success, error, skipped, or partial
  - error_message: Details if execution failed
- Tracks performance metrics:
  - transformation_time_ms: Time spent transforming data
  - api_call_time_ms: Time spent calling target API
- Indexed by created_at, status, and integration for fast queries

### Processing Flow

#### Webhook Flow
1. **Webhook receives POST** → Django view receives JSON payload
2. **Load configuration** → Get integration by webhook path
3. **Evaluate condition** → Run JavaScript condition if configured
4. **Transform data** → Apply field mappings and transformations
5. **Route to target** → HTTP, Email, or SMS based on target type
6. **Authenticate** → Add auth headers for HTTP targets
7. **Send request** → Execute HTTP call or send email/SMS
8. **Log result** → Create IntegrationRun record with all details

#### Pub/Sub Push Flow
1. **Google Pub/Sub pushes** → Django view receives base64-encoded message
2. **Decode message** → Extract JSON data from Pub/Sub envelope
3. **Load configuration** → Get integration by push endpoint
4. **Process through pipeline** → Same as webhook (condition → transform → send)
5. **Return 204** → Acknowledge message receipt to Google

#### Pub/Sub Pull Flow
1. **Background thread wakes** → Scheduler checks for messages at interval
2. **Pull messages** → Request up to 10 messages from subscription
3. **For each message**:
   - Decode and parse JSON data
   - Process through integration pipeline
   - Log execution result
4. **Acknowledge messages** → Tell Google Pub/Sub messages were processed
5. **Sleep until next interval** → Wait for configured pull_interval_seconds

### Key Components

**integration_processor.py**
- Core processing logic for all integration types
- Handles transformation, authentication, and target routing
- Routes to: process_http_integration, process_email_integration, or process_sms_integration
- Creates IntegrationRun records with performance metrics

**pubsub_manager.py**
- Google Cloud Pub/Sub client wrapper
- Functions: create_push_subscription, create_pull_subscription, delete_subscription
- pull_messages: Retrieve and acknowledge messages
- publish_test_message: Test integration by sending sample data
- handle_pubsub_push: Decode push notification payloads

**pubsub_scheduler.py**
- Background thread scheduler for pull subscriptions
- PubSubPullScheduler class manages active pullers
- One thread per active pull integration
- Graceful start/stop with threading events
- Handles errors without stopping scheduler

### Django Admin

**Integration Configurations**
- List view with filters (source type, method, status)
- Detail view with full configuration
- "Open Editor" link to frontend mapper
- Toggle active/inactive status

**Integration Runs**
- List view with filters (status, date, integration)
- Read-only detail view showing:
  - Incoming payload
  - Transformed payload
  - Outgoing request
  - Outgoing response
  - Error messages
  - Performance metrics

## Frontend Integration

### Saving to Backend

```javascript
// Initialize mapper with backend URL
const mapper = new JSONMapper({
  container: '#mapper-container',
  apiBaseUrl: '/api'  // Django API base URL
});

// Save integration
await mapper.saveIntegrationToBackend();
```

### Loading from Backend

```javascript
// Load by ID
await mapper.loadIntegrationFromBackend('integration-uuid');

// Or from URL parameter
// Navigate to: /mapper/?integration_id=integration-uuid
```

### Viewing Integration Runs

```javascript
// Get runs for current integration
const runs = await mapper.getIntegrationRuns(integrationId);

// Display in modal
showIntegrationRunsDialog();
```

## Deployment

### Using Docker Compose

```bash
# Build and start services
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Start Pub/Sub listeners
docker-compose exec web python manage.py start_pubsub_listeners
```

### Manual Deployment

1. Set up PostgreSQL database
2. Configure environment variables
3. Run migrations: `python manage.py migrate`
4. Collect static files: `python manage.py collectstatic`
5. Start Gunicorn: `gunicorn config.wsgi:application`
6. Start Pub/Sub listeners: `python manage.py start_pubsub_listeners`
7. Configure nginx/Apache as reverse proxy

### Environment Variables

```bash
# Django settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# CORS (for frontend on different domain)
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Site URL - IMPORTANT: Set to your actual domain
# This is used for webhook URLs and Pub/Sub push endpoints
# Examples:
#   Development: http://localhost:8000
#   Production:  https://integrations.yourdomain.com
SITE_URL=https://yourdomain.com
```

**IMPORTANT**: The `SITE_URL` setting is critical for:
- Webhook URL generation (e.g., `https://yourdomain.com/webhook/abc123/`)
- Pub/Sub push endpoints (e.g., `https://yourdomain.com/pubsub/xyz789/`)
- Must be publicly accessible for Pub/Sub push mode to work

## Google Cloud Pub/Sub Setup

### Prerequisites
1. Create a GCP project at https://console.cloud.google.com
2. Enable Pub/Sub API in APIs & Services
3. Create a topic for your integration
4. Create a service account with appropriate permissions

### Service Account Permissions

For **Push Mode**:
- `pubsub.subscriptions.create`
- `pubsub.subscriptions.update`
- `pubsub.subscriptions.delete`
- `pubsub.topics.attachSubscription`

For **Pull Mode** (requires additional):
- `pubsub.subscriptions.consume` (to pull messages)
- `pubsub.subscriptions.get`

Recommended role: **Pub/Sub Editor** (`roles/pubsub.editor`)

### Getting Service Account JSON

1. Go to **IAM & Admin** → **Service Accounts**
2. Create or select service account
3. Click **Keys** → **Add Key** → **Create New Key**
4. Select **JSON** format
5. Download the JSON file
6. Paste the entire JSON content into the frontend credentials field

### Testing Setup

You can test your Pub/Sub configuration using gcloud CLI:

```bash
# Publish test message
gcloud pubsub topics publish YOUR_TOPIC --message '{"test": "data"}'

# Check subscription exists
gcloud pubsub subscriptions list

# Pull messages manually (for troubleshooting)
gcloud pubsub subscriptions pull YOUR_SUBSCRIPTION --limit=5
```

## Security Considerations

1. **CSRF Protection**: Enabled by default for all POST/PUT/DELETE requests
2. **Authentication**: Configure `REST_FRAMEWORK` permissions for API access
3. **HTTPS**: Use HTTPS in production for webhook endpoints
4. **Secrets**: Store API keys and tokens securely (use environment variables)
5. **Rate Limiting**: Add rate limiting to webhook endpoints
6. **Input Validation**: JSON payloads are validated before processing

## Monitoring and Logging

### Application Logs

Django logs all integration executions to IntegrationRun model:
- Success/error status
- Performance metrics
- Full request/response data

### Querying Logs

```python
# Get all failed runs
failed_runs = IntegrationRun.objects.filter(status='error')

# Get runs for specific integration
integration_runs = IntegrationRun.objects.filter(
    integration_id='uuid'
).order_by('-created_at')

# Get slow runs
slow_runs = IntegrationRun.objects.filter(
    api_call_time_ms__gt=5000
)
```

### Performance Monitoring

Add to your settings for database query monitoring:
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Troubleshooting

### Webhook not receiving data
1. Check integration is active: `IntegrationConfiguration.objects.get(id=X).is_active`
2. Verify webhook path matches
3. Check Django logs for errors
4. Test with curl: `curl -X POST https://domain.com/webhook/path/ -H "Content-Type: application/json" -d '{"test": "data"}'`

### Pub/Sub not receiving messages

**Push Mode Issues:**
1. Verify service account credentials are valid JSON
2. Check subscription exists: `gcloud pubsub subscriptions list`
3. Ensure `SITE_URL` environment variable is set correctly
4. Verify push endpoint is publicly accessible (not localhost)
5. Check `pubsub_listener_active` field is `True`
6. Review Django logs for push handler errors
7. Test endpoint manually: `curl -X POST https://yourdomain.com/pubsub/path/`

**Pull Mode Issues:**
1. Verify service account has `pubsub.subscriptions.consume` permission
2. Check if pull scheduler thread is running (look for log message)
3. Verify `pubsub_pull_interval_seconds` is set appropriately
4. Check subscription exists: `gcloud pubsub subscriptions list`
5. Manually pull to test: `gcloud pubsub subscriptions pull YOUR_SUBSCRIPTION`
6. Review Django logs for pull scheduler errors
7. Restart Django server to restart pull threads

### API calls failing
1. Check IntegrationRun logs for error messages
2. Verify target URL is accessible
3. Check authentication configuration
4. Test target API directly with curl
5. Verify network/firewall settings

### Performance issues
1. Add database indexes on frequently queried fields
2. Use database connection pooling
3. Enable Redis caching
4. Use Celery for async processing of large payloads
5. Monitor database query performance

## Advanced Configuration

### Celery for Async Processing

For high-volume integrations, process webhooks asynchronously:

```python
# tasks.py
from celery import shared_task
from integrations.integration_processor import process_integration

@shared_task
def process_integration_async(integration_id, payload):
    integration = IntegrationConfiguration.objects.get(id=integration_id)
    return process_integration(integration, payload)

# views.py
@csrf_exempt
@api_view(['POST'])
def webhook_handler(request, webhook_path):
    integration = get_object_or_404(...)
    
    # Process asynchronously
    process_integration_async.delay(
        str(integration.id), 
        request.data
    )
    
    return JsonResponse({'status': 'queued'})
```

### Custom Transformations

Add custom transformation functions:

```python
# integrations/transformations.py
def custom_transform(value, *params):
    # Your custom logic
    return transformed_value

# Register in integration_processor.py
CUSTOM_TRANSFORMS = {
    'my_transform': custom_transform
}
```

### Webhook Rate Limiting

Add rate limiting using Django Ratelimit:

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='100/m', method='POST')
@csrf_exempt
@api_view(['POST'])
def webhook_handler(request, webhook_path):
    # Your handler code
    pass
```

### Database Optimization

Add indexes for better query performance:

```python
class IntegrationRun(models.Model):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['-created_at', 'status']),
            models.Index(fields=['integration', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
```

## Testing

Run tests:
```bash
python manage.py test integrations
```

With coverage:
```bash
coverage run --source='.' manage.py test integrations
coverage report
coverage html  # Generate HTML report
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Frontend Features

### Visual Mapper Interface

The frontend provides an intuitive 4-step workflow:

**Step 1: Configure Integration**
- Name your integration
- Choose source type (Webhook or Pub/Sub)
- Choose target type (HTTP or Email)
- Configure authentication and settings

**Step 2: Define Mappings**
- Add source JSON sample data
- Create field mappings with drag-and-drop
- Apply transformations:
  - `uppercase`, `lowercase` - Change text case
  - `substring(start, length)` - Extract substring
  - `replace(find, replace)` - Replace text
  - `default(value)` - Provide fallback value
  - `concat(field1, field2, ...)` - Combine fields
  - `custom(js)` - Write custom JavaScript
- Add conditions to skip/process based on data

**Step 3: Test Integration**
- Preview transformed output
- View integration run history

**Step 4: Save & Execute**
- Validate integration before saving
- Save to backend (creates subscription/webhook)
- Execute full integration test
- View real-time results

### Change Tracking

The frontend tracks changes and enforces validation:
1. Any modification marks integration as "changed"
2. "Save to Backend" button is hidden until validation
3. Click "Validate Integration" to check configuration
4. Only after successful validation can you save
5. This prevents saving broken configurations

## Example Use Cases

### 1. Webhook → Slack Notification
Receive webhook from payment processor, transform data, send to Slack:
- Source: Webhook
- Transform: Extract amount, customer name, status
- Target: HTTP POST to Slack webhook URL
- Result: Instant Slack notifications for new payments

### 2. Pub/Sub → Email Alert
Pull messages from GCP Pub/Sub, send email alerts:
- Source: Pub/Sub (Pull mode, check every 30 seconds)
- Condition: `data.severity === 'critical'`
- Transform: Format error details
- Target: Email via SMTP
- Result: Automated critical error notifications

### 3. Pub/Sub → Multi-Target
Process Pub/Sub messages and route to different targets based on data:
- Create multiple integrations for same topic
- Use conditions to route: `data.type === 'order'`
- Each integration sends to different target
- Result: Event-driven microservices integration

## Technology Stack

**Backend:**
- Django 4.2+ with Django REST Framework
- PostgreSQL for data persistence
- Google Cloud Pub/Sub Python client
- Threading for background pull schedulers
- SMTP for email and SMS delivery

**Frontend:**
- Vanilla JavaScript (no framework dependencies)
- Responsive CSS with Django Daisy autumn theme
- Fetch API for backend communication
- Local storage for draft integrations

**Infrastructure:**
- Docker & Docker Compose support
- Gunicorn WSGI server
- Nginx reverse proxy ready
- Environment-based configuration

## Support

For issues and questions, refer to the troubleshooting section above or check:
- Django logs: `python manage.py runserver` output
- Integration runs: Django Admin → Integration Runs
- Database: Query IntegrationRun model for details

## Future Improvement

- Security: Store Pub/Sub credentials encrypted in a vault.
- Security: Store SMTP config JSON in a vault.
- Pub/Sub Pull Scheduler: Add implementation to start/stop scheduler when server is started or integration is inactive.