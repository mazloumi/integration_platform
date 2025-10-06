# tests.py
from django.test import TestCase
from rest_framework.test import APIClient
from integrations.models import IntegrationConfiguration, IntegrationRun
import json


class IntegrationAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        self.integration_config = {
            "name": "Test Integration",
            "sourceType": "webhook",
            "sourceConfig": {},
            "target": {
                "method": "POST",
                "url": "https://api.example.com/test",
                "authType": "none",
                "auth": {},
                "headers": {}
            },
            "mappings": [
                {
                    "source": "name",
                    "target": "full_name",
                    "transform": "uppercase",
                    "params": [],
                    "jsCode": "",
                    "sourceFields": []
                }
            ]
        }
    
    def test_create_integration(self):
        """Test creating a new integration"""
        response = self.client.post(
            '/api/integrations/',
            {
                'name': 'Test Integration',
                'config_json': self.integration_config
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('webhook_path', response.data)
        self.assertIn('webhook_url', response.data)
    
    def test_get_integration(self):
        """Test retrieving an integration"""
        integration = IntegrationConfiguration.objects.create(
            name='Test Integration',
            config_json=self.integration_config,
            source_type='webhook',
            target_url='https://api.example.com/test',
            target_method='POST',
            webhook_path='/webhook/test123'
        )
        
        response = self.client.get(f'/api/integrations/{integration.id}/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'Test Integration')
    
    def test_update_integration(self):
        """Test updating an integration"""
        integration = IntegrationConfiguration.objects.create(
            name='Test Integration',
            config_json=self.integration_config,
            source_type='webhook',
            target_url='https://api.example.com/test',
            target_method='POST',
            webhook_path='/webhook/test123'
        )
        
        updated_config = self.integration_config.copy()
        updated_config['name'] = 'Updated Integration'
        
        response = self.client.put(
            f'/api/integrations/{integration.id}/',
            {
                'name': 'Updated Integration',
                'config_json': updated_config
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'Updated Integration')
    
    def test_webhook_endpoint(self):
        """Test webhook endpoint processing"""
        integration = IntegrationConfiguration.objects.create(
            name='Test Integration',
            config_json=self.integration_config,
            source_type='webhook',
            target_url='https://httpbin.org/post',
            target_method='POST',
            webhook_path='/webhook/test123',
            is_active=True
        )
        
        webhook_data = {
            'name': 'john doe',
            'email': 'john@example.com'
        }
        
        response = self.client.post(
            f'/webhook/test123/',
            webhook_data,
            format='json'
        )
        
        # Should create an integration run
        self.assertEqual(IntegrationRun.objects.count(), 1)
        
        run = IntegrationRun.objects.first()
        self.assertEqual(run.integration, integration)
        self.assertEqual(run.incoming_payload, webhook_data)
