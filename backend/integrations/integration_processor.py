# integration_processor.py
import requests
import time
from typing import Dict, Any
from .models import IntegrationConfiguration, IntegrationRun


def process_integration(integration: IntegrationConfiguration, incoming_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an integration: transform data and send to target API or email
    """
    start_time = time.time()

    try:
        # Load configuration
        config = integration.config_json
        mappings = config.get('mappings', [])
        condition = config.get('condition')

        # Evaluate condition if present
        condition_result = True
        if condition:
            condition_result = evaluate_condition(condition, incoming_payload)
            print("Condition result")
            print(condition_result)
            if not condition_result:
                # Log the run as skipped
                print("Condition not true")
                run = IntegrationRun.objects.create(
                    integration=integration,
                    incoming_payload=incoming_payload,
                    transformed_payload={},
                    outgoing_request={
                        'skipped': True,
                        'reason': 'Condition evaluated to false',
                        'condition': condition,
                        'condition_result': False
                    },
                    outgoing_response={'skipped': True},
                    status='skipped',
                    error_message='Condition not met - execution skipped',
                    transformation_time_ms=0,
                    api_call_time_ms=0
                )
                return {
                    'run_id': run.id,
                    'status': 'skipped',
                    'message': 'Condition evaluated to false'
                }

        print("Condition is true")
        # Transform data
        transform_start = time.time()
        transformed_payload = transform_data(incoming_payload, mappings)
        transformation_time = int((time.time() - transform_start) * 1000)

        # Check if target type is email or SMS
        target_config = config.get('target', {})
        target_type = target_config.get('type', 'http')

        if target_type == 'email':
            return process_email_integration(integration, incoming_payload, transformed_payload, transformation_time, condition, condition_result)

        # Prepare API request
        target_config = config.get('target', {})
        headers = target_config.get('headers', {})
        auth_config = target_config.get('auth', {})
        
        # Add authentication
        headers = add_authentication(headers, target_config.get('authType'), auth_config)
        
        # Make API call
        api_start = time.time()
        if target_config.get('method') == 'GET':
            response = requests.get(
                integration.target_url,
                params=flatten_dict(transformed_payload),
                headers=headers,
                timeout=30
            )
        else:  # POST
            headers['Content-Type'] = 'application/json'
            response = requests.post(
                integration.target_url,
                json=transformed_payload,
                headers=headers,
                timeout=30
            )
        
        api_call_time = int((time.time() - api_start) * 1000)
        
        # Parse response
        try:
            response_data = response.json()
        except:
            response_data = {'body': response.text}
        
        # Log the run
        run = IntegrationRun.objects.create(
            integration=integration,
            incoming_payload=incoming_payload,
            transformed_payload=transformed_payload,
            outgoing_request={
                'url': integration.target_url,
                'method': target_config.get('method'),
                'headers': {k: v for k, v in headers.items() if k.lower() != 'authorization'},
                'body': transformed_payload,
                'condition': condition if condition else None,
                'condition_result': condition_result if condition else None
            },
            outgoing_response={
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': response_data
            },
            status='success' if response.ok else 'error',
            error_message=None if response.ok else f"HTTP {response.status_code}",
            transformation_time_ms=transformation_time,
            api_call_time_ms=api_call_time
        )
        
        return {
            'run_id': run.id,
            'status': 'success' if response.ok else 'error',
            'response': response_data
        }
    
    except Exception as e:
        # Log failed run
        run = IntegrationRun.objects.create(
            integration=integration,
            incoming_payload=incoming_payload,
            transformed_payload={},
            outgoing_request={'error': 'Failed before request'},
            outgoing_response={'error': str(e)},
            status='error',
            error_message=str(e),
            transformation_time_ms=0,
            api_call_time_ms=0
        )
        
        raise


def transform_data(source_data: Dict[str, Any], mappings: list) -> Dict[str, Any]:
    """Transform source data using mappings"""
    output = {}

    for mapping in mappings:
        target = mapping.get('target')
        if not target:
            continue

        try:
            if mapping.get('transform') == 'javascript':
                # JavaScript transformation
                js_code = mapping.get('jsCode')
                source_fields = mapping.get('sourceFields', [])

                if not js_code:
                    continue

                # Build fields object for JavaScript
                fields = {}
                for field_path in source_fields:
                    fields[field_path] = get_nested_value(source_data, field_path)

                # Execute JavaScript transformation
                value = execute_javascript_transform(js_code, fields)
            else:
                source = mapping.get('source')
                if not source:
                    continue

                value = get_nested_value(source_data, source)

                # Apply transformation
                transform = mapping.get('transform')
                params = mapping.get('params', [])
                value = apply_transformation(value, transform, params)

            set_nested_value(output, target, value)

        except Exception as e:
            print(f"Error in mapping {target}: {e}")
            continue

    return output


def get_nested_value(obj: Dict, path: str) -> Any:
    """Get nested value from dictionary using dot notation"""
    keys = path.split('.')
    for key in keys:
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return None
        if obj is None:
            return None
    return obj


def set_nested_value(obj: Dict, path: str, value: Any):
    """Set nested value in dictionary using dot notation"""
    keys = path.split('.')
    for key in keys[:-1]:
        if key not in obj:
            obj[key] = {}
        obj = obj[key]
    obj[keys[-1]] = value


def apply_transformation(value: Any, transform: str, params: list) -> Any:
    """Apply transformation to value"""
    if transform == 'uppercase':
        return str(value).upper() if value is not None else None
    elif transform == 'lowercase':
        return str(value).lower() if value is not None else None
    elif transform == 'trim':
        return str(value).strip() if value is not None else None
    elif transform == 'number':
        return float(value) if value is not None else None
    elif transform == 'string':
        return str(value) if value is not None else None
    elif transform == 'boolean':
        return bool(value) if value is not None else None
    elif transform == 'concat':
        return str(value) + str(params[0] if params else '') if value is not None else None
    elif transform == 'replace':
        search = params[0] if len(params) > 0 else ''
        replace = params[1] if len(params) > 1 else ''
        return str(value).replace(search, replace) if value is not None else None
    elif transform == 'split':
        delim = params[0] if params else ','
        return str(value).split(delim) if value is not None else None
    elif transform == 'join':
        delim = params[0] if params else ','
        return delim.join(value) if isinstance(value, list) else value
    else:
        return value


def add_authentication(headers: Dict, auth_type: str, auth_config: Dict) -> Dict:
    """Add authentication headers"""
    headers = headers.copy()
    
    if auth_type == 'bearer':
        headers['Authorization'] = f"Bearer {auth_config.get('token', '')}"
    elif auth_type == 'basic':
        import base64
        credentials = f"{auth_config.get('username', '')}:{auth_config.get('password', '')}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers['Authorization'] = f"Basic {encoded}"
    elif auth_type == 'apikey':
        header_name = auth_config.get('headerName', 'X-API-Key')
        headers[header_name] = auth_config.get('apiKey', '')
    
    return headers


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """Flatten nested dictionary for GET parameters"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def evaluate_condition(condition_code: str, source_data: Dict[str, Any]) -> bool:
    """
    Evaluate a JavaScript condition.
    Tries Js2Py first, then falls back to Python evaluation.
    """
    # Build fields dictionary
    fields = {}
    flatten_fields(source_data, fields)

    # Try using Js2Py for JavaScript evaluation
    try:
        import js2py
        import json

        # Create JavaScript context with fields
        fields_json = json.dumps(fields)

        js_code = f"""
        var fields = {fields_json};
        (function() {{
            {condition_code}
        }})();
        """

        # Evaluate JavaScript
        result = js2py.eval_js(js_code)
        return bool(result)

    except ImportError:
        # Fallback: Simple Python-based evaluation
        print("Warning: Js2Py not installed. Using Python-based condition evaluation.")
        print("Install with: pip install Js2Py")

        # Simple Python eval (SECURITY WARNING: Only for trusted conditions)
        # Replace JavaScript syntax with Python equivalents
        python_condition = condition_code.replace('===', '==').replace('!==', '!=').replace('&&', ' and ').replace('||', ' or ')

        try:
            # Evaluate in restricted namespace
            namespace = {'fields': fields, 'True': True, 'False': False, 'None': None}
            result = eval(python_condition, {"__builtins__": {}}, namespace)
            return bool(result)
        except Exception as e:
            print(f"Error evaluating condition: {e}")
            return True  # Default to true if evaluation fails

    except Exception as e:
        print(f"Error in condition evaluation: {e}")
        return True  # Default to true if evaluation fails


def execute_javascript_transform(js_code: str, fields: Dict[str, Any]) -> Any:
    """
    Execute JavaScript transformation code using Js2Py.
    Falls back to Python evaluation if Js2Py is not available.
    """
    # Try using Js2Py for JavaScript evaluation
    try:
        import js2py
        import json

        # Prepare fields as JSON
        fields_json = json.dumps(fields)

        # Create JavaScript context with fields
        js_full_code = f"""
        var fields = {fields_json};
        (function() {{
            {js_code}
        }})();
        """

        # Evaluate JavaScript and return result
        result = js2py.eval_js(js_full_code)

        # Convert Js2Py objects to Python native types
        if hasattr(result, 'to_dict'):
            return result.to_dict()
        elif hasattr(result, 'to_list'):
            return result.to_list()
        else:
            return result

    except ImportError:
        # Fallback: Simple Python-based evaluation
        print("Warning: Js2Py not installed. JavaScript transformations may not work correctly.")
        print("Install with: pip install Js2Py")

        # Simple Python eval (SECURITY WARNING: Only for trusted code)
        # Replace JavaScript syntax with Python equivalents
        python_code = js_code.replace('===', '==').replace('!==', '!=').replace('&&', ' and ').replace('||', ' or ')

        try:
            # Evaluate in restricted namespace
            namespace = {'fields': fields, 'True': True, 'False': False, 'None': None}
            result = eval(python_code, {"__builtins__": {}}, namespace)
            return result
        except Exception as e:
            print(f"Error evaluating JavaScript transform: {e}")
            return None

    except Exception as e:
        print(f"Error in JavaScript transformation: {e}")
        return None


def flatten_fields(obj: Any, fields: Dict, prefix: str = '') -> None:
    """Flatten nested object into fields dictionary with dot notation"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                flatten_fields(value, fields, new_key)
            fields[new_key] = value
    elif isinstance(obj, list):
        fields[prefix] = obj
    else:
        if prefix:
            fields[prefix] = obj


def process_email_integration(integration: IntegrationConfiguration, incoming_payload: Dict[str, Any],
                              transformed_payload: Dict[str, Any], transformation_time: int,
                              condition: str = None, condition_result: bool = True) -> Dict[str, Any]:
    """
    Process email integration: send transformed data as email
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import json

    config = integration.config_json
    target_config = config.get('target', {})
    email_config = target_config.get('emailConfig', {})

    try:
        # Extract email configuration
        smtp_server = email_config.get('smtpServer')
        smtp_port = email_config.get('smtpPort', 587)
        smtp_username = email_config.get('smtpUsername')
        smtp_password = email_config.get('smtpPassword')
        from_email = email_config.get('fromEmail')
        to_email = email_config.get('toEmail', '')
        subject = email_config.get('subject', 'Integration Notification')
        use_tls = email_config.get('useTLS', True)

        # Parse recipient emails (comma-separated)
        to_emails = [email.strip() for email in to_email.split(',') if email.strip()]

        # Create email
        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject

        # Create email body with transformed data
        email_body = json.dumps(transformed_payload, indent=2)
        text_part = MIMEText(email_body, 'plain')
        msg.attach(text_part)

        # Send email
        email_start = time.time()

        if use_tls:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)

        server.login(smtp_username, smtp_password)
        server.sendmail(from_email, to_emails, msg.as_string())
        server.quit()

        email_time = int((time.time() - email_start) * 1000)

        # Log the run
        run = IntegrationRun.objects.create(
            integration=integration,
            incoming_payload=incoming_payload,
            transformed_payload=transformed_payload,
            outgoing_request={
                'type': 'email',
                'smtp_server': smtp_server,
                'from': from_email,
                'to': to_emails,
                'subject': subject,
                'body': transformed_payload,
                'condition': condition if condition else None,
                'condition_result': condition_result if condition else None
            },
            outgoing_response={
                'status': 'sent',
                'recipients': to_emails,
                'message': 'Email sent successfully'
            },
            status='success',
            error_message=None,
            transformation_time_ms=transformation_time,
            api_call_time_ms=email_time
        )

        return {
            'run_id': run.id,
            'status': 'success',
            'message': f'Email sent to {len(to_emails)} recipient(s)'
        }

    except Exception as e:
        # Log failed run
        run = IntegrationRun.objects.create(
            integration=integration,
            incoming_payload=incoming_payload,
            transformed_payload=transformed_payload,
            outgoing_request={
                'type': 'email',
                'error': 'Failed to send email'
            },
            outgoing_response={'error': str(e)},
            status='error',
            error_message=str(e),
            transformation_time_ms=transformation_time,
            api_call_time_ms=0
        )

        raise


