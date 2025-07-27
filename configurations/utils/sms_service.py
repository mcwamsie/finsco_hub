import requests
import json
import logging
from django.conf import settings
from django.utils import timezone
from typing import Dict, Optional, List

from configurations.models import SMSGateway
from configurations.models.sms_gateway import SMSMessage

logger = logging.getLogger(__name__)


class SMSService:
    """Service class for sending SMS messages through configured gateways"""

    def __init__(self, gateway: Optional[SMSGateway] = None):
        self.gateway = gateway or self.get_primary_gateway()
        if not self.gateway:
            raise ValueError("No SMS gateway configured")

    @staticmethod
    def get_primary_gateway() -> Optional[SMSGateway]:
        """Get the primary SMS gateway"""
        return SMSGateway.objects.filter(is_active=True, is_primary=True).first()

    def send_sms(self, recipient: str, message: str, message_type: str = 'notification',
                 priority: str = 'normal', sender_id: str = None) -> Dict:
        """Send SMS message through the gateway"""

        try:
            # Create SMS message record
            sms_message = SMSMessage.objects.create(
                gateway=self.gateway,
                recipient_number=self.format_phone_number(recipient),
                message_content=message,
                message_type=message_type,
                priority=priority,
                sender_id=sender_id or self.gateway.sender_id,
                status='pending'
            )

            # Prepare request data
            request_data = self.prepare_request_data(sms_message)

            # Send request to gateway
            response = self.send_to_gateway(request_data)

            # Process response
            result = self.process_gateway_response(sms_message, response)

            return result

        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message_id': None
            }

    def prepare_request_data(self, sms_message: SMSMessage) -> Dict:
        """Prepare request data based on gateway mappings"""

        data = {}

        # Get field mappings for this gateway
        mappings = self.gateway.field_mappings.all()

        for mapping in mappings:
            value = None

            if mapping.field_type == 'recipient':
                value = sms_message.recipient_number
            elif mapping.field_type == 'message':
                value = sms_message.message_content
            elif mapping.field_type == 'sender':
                value = sms_message.sender_id
            elif mapping.field_type == 'message_id':
                value = sms_message.message_id
            elif mapping.default_value:
                value = mapping.default_value

            # Apply format rule if specified
            if value and mapping.format_rule:
                if '{number}' in mapping.format_rule:
                    value = mapping.format_rule.format(number=value.replace('+', ''))
                else:
                    value = mapping.format_rule.format(value=value)

            if value:
                data[mapping.gateway_field_name] = value

        return data

    def send_to_gateway(self, data: Dict) -> requests.Response:
        """Send request to SMS gateway"""

        url = f"{self.gateway.base_url.rstrip('/')}/{self.gateway.api_endpoint.lstrip('/')}"

        headers = {
            'Content-Type': 'application/json',
        }

        # Add authentication headers
        if self.gateway.auth_type == 'header':
            headers['Username'] = self.gateway.username
            headers['Password'] = self.gateway.password
        elif self.gateway.auth_type == 'api_key':
            headers['Authorization'] = f'ApiKey {self.gateway.api_key}'
        elif self.gateway.auth_type == 'bearer':
            headers['Authorization'] = f'Bearer {self.gateway.api_key}'
        elif self.gateway.auth_type == 'basic':
            import base64
            credentials = base64.b64encode(
                f"{self.gateway.username}:{self.gateway.password}".encode()
            ).decode()
            headers['Authorization'] = f'Basic {credentials}'

        # Send request
        response = requests.post(
            url=url,
            headers=headers,
            json=data,
            timeout=self.gateway.timeout_seconds if hasattr(self.gateway, 'timeout_seconds') else 30
        )

        return response

    def process_gateway_response(self, sms_message: SMSMessage, response: requests.Response) -> Dict:
        """Process gateway response and update message status"""

        try:
            response_data = response.json() if response.content else {}
        except:
            response_data = {'raw_response': response.text}

        # Update message with response
        sms_message.gateway_response = response_data

        if response.status_code == 200:
            sms_message.status = 'sent'
            sms_message.sent_at = timezone.now()

            # Extract gateway message ID if available
            gateway_id_field = 'message_id'  # Common field name
            if gateway_id_field in response_data:
                sms_message.gateway_message_id = response_data[gateway_id_field]

            sms_message.save()

            return {
                'success': True,
                'message_id': sms_message.message_id,
                'gateway_message_id': sms_message.gateway_message_id,
                'status': 'sent'
            }
        else:
            sms_message.status = 'failed'
            sms_message.save()

            return {
                'success': False,
                'message_id': sms_message.message_id,
                'error': f"Gateway error: {response.status_code}",
                'response': response_data
            }

    def format_phone_number(self, phone: str) -> str:
        """Format phone number for the gateway"""

        # Remove any non-digit characters except +
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')

        # Add country code if missing (assuming Zimbabwe +263)
        if not phone.startswith('+'):
            if phone.startswith('0'):
                phone = '+263' + phone[1:]
            elif not phone.startswith('263'):
                phone = '+263' + phone
            else:
                phone = '+' + phone

        return phone

    def send_bulk_sms(self, recipients: List[str], message: str,
                      message_type: str = 'notification') -> Dict:
        """Send SMS to multiple recipients"""

        results = []
        success_count = 0

        for recipient in recipients:
            result = self.send_sms(recipient, message, message_type)
            results.append({
                'recipient': recipient,
                'success': result['success'],
                'message_id': result.get('message_id'),
                'error': result.get('error')
            })

            if result['success']:
                success_count += 1

        return {
            'total_sent': len(recipients),
            'successful': success_count,
            'failed': len(recipients) - success_count,
            'results': results
        }