import requests
import json
import logging
from django.conf import settings
from django.utils import timezone
from typing import Dict, Optional
from configurations.models import PaymentGateway, PaymentGatewayToken, PaymentGatewayRequest

logger = logging.getLogger(__name__)


class PaymentGatewayService:
    """Service class for handling payment gateway operations with JWT token management"""

    def __init__(self, gateway: PaymentGateway):
        self.gateway = gateway

    def get_valid_token(self) -> Optional[str]:
        """Get a valid JWT token, refreshing if necessary"""

        if self.gateway.auth_type != 'jwt':
            return None

        try:
            token_info = self.gateway.token_info

            # Check if token exists and is not expired
            if token_info and not token_info.is_expired:
                # Refresh if expires soon
                if token_info.expires_soon:
                    self.refresh_token()
                return token_info.access_token

            # Get new token if no valid token exists
            return self.authenticate()

        except PaymentGatewayToken.DoesNotExist:
            return self.authenticate()

    def authenticate(self) -> Optional[str]:
        """Authenticate with the gateway and get JWT token"""

        if not self.gateway.login_url:
            raise ValueError("Login URL not configured for JWT authentication")

        try:
            # Prepare login request
            login_data = {
                'username': self.gateway.username,
                'password': self.gateway.password
            }

            if self.gateway.merchant_id:
                login_data['merchant_id'] = self.gateway.merchant_id

            headers = {
                'Content-Type': 'application/json'
            }

            # Send login request
            response = requests.post(
                url=self.gateway.login_url,
                headers=headers,
                json=login_data,
                timeout=self.gateway.timeout_seconds
            )

            if response.status_code == 200:
                response_data = response.json()

                # Extract token information
                access_token = response_data.get(self.gateway.token_field_name)
                refresh_token = response_data.get(self.gateway.refresh_token_field_name)
                expires_in = response_data.get(self.gateway.token_expires_in_field, 3600)

                if access_token:
                    # Store or update token
                    token_info, created = PaymentGatewayToken.objects.update_or_create(
                        gateway=self.gateway,
                        defaults={
                            'access_token': access_token,
                            'refresh_token': refresh_token,
                            'expires_in': expires_in,
                            'expires_at': timezone.now() + timezone.timedelta(seconds=expires_in),
                            'is_active': True
                        }
                    )

                    logger.info(f"{'Created' if created else 'Updated'} token for gateway {self.gateway.name}")
                    return access_token

            logger.error(f"Authentication failed for gateway {self.gateway.name}: {response.status_code}")
            return None

        except Exception as e:
            logger.error(f"Authentication error for gateway {self.gateway.name}: {str(e)}")
            return None

    def refresh_token(self) -> Optional[str]:
        """Refresh the JWT token"""

        if not self.gateway.token_refresh_url:
            # If no refresh URL, get new token
            return self.authenticate()

        try:
            token_info = self.gateway.token_info

            if not token_info.refresh_token:
                return self.authenticate()

            refresh_data = {
                self.gateway.refresh_token_field_name: token_info.refresh_token
            }

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token_info.access_token}'
            }

            response = requests.post(
                url=self.gateway.token_refresh_url,
                headers=headers,
                json=refresh_data,
                timeout=self.gateway.timeout_seconds
            )

            if response.status_code == 200:
                response_data = response.json()

                access_token = response_data.get(self.gateway.token_field_name)
                new_refresh_token = response_data.get(self.gateway.refresh_token_field_name)
                expires_in = response_data.get(self.gateway.token_expires_in_field, 3600)

                if access_token:
                    # Update token info
                    token_info.access_token = access_token
                    if new_refresh_token:
                        token_info.refresh_token = new_refresh_token
                    token_info.expires_in = expires_in
                    token_info.expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
                    token_info.last_refreshed_at = timezone.now()
                    token_info.save()

                    logger.info(f"Refreshed token for gateway {self.gateway.name}")
                    return access_token

            # If refresh fails, get new token
            return self.authenticate()

        except Exception as e:
            logger.error(f"Token refresh error for gateway {self.gateway.name}: {str(e)}")
            return self.authenticate()

    def process_payment(self, payment_data: Dict) -> Dict:
        """Process payment through the gateway"""

        try:
            # Generate request ID
            import uuid
            request_id = f"PAY{timezone.now().strftime('%y%m%d')}{str(uuid.uuid4())[:8].upper()}"

            # Prepare headers
            headers = {
                'Content-Type': 'application/json'
            }

            # Add authentication
            if self.gateway.auth_type == 'jwt':
                token = self.get_valid_token()
                if not token:
                    raise Exception("Failed to obtain valid token")
                headers['Authorization'] = f'Bearer {token}'
            elif self.gateway.auth_type == 'api_key':
                headers['Authorization'] = f'ApiKey {self.gateway.api_key}'
            elif self.gateway.auth_type == 'basic':
                import base64
                credentials = base64.b64encode(
                    f"{self.gateway.username}:{self.gateway.password}".encode()
                ).decode()
                headers['Authorization'] = f'Basic {credentials}'

            # Prepare payment URL
            payment_url = f"{self.gateway.base_url.rstrip('/')}/payment"

            # Create request record
            gateway_request = PaymentGatewayRequest.objects.create(
                gateway=self.gateway,
                payment_method=payment_data.get('payment_method'),
                request_id=request_id,
                request_type='payment',
                request_url=payment_url,
                request_method='POST',
                request_headers=headers,
                request_data=payment_data,
                status='pending'
            )

            # Send payment request
            start_time = timezone.now()
            response = requests.post(
                url=payment_url,
                headers=headers,
                json=payment_data,
                timeout=self.gateway.timeout_seconds
            )
            end_time = timezone.now()

            # Calculate processing time
            processing_time = int((end_time - start_time).total_seconds() * 1000)

            # Update request record
            gateway_request.response_status_code = response.status_code
            gateway_request.response_headers = dict(response.headers)
            gateway_request.response_timestamp = end_time
            gateway_request.processing_time_ms = processing_time

            try:
                response_data = response.json()
                gateway_request.response_data = response_data
            except:
                gateway_request.response_data = {'raw_response': response.text}

            if response.status_code == 200:
                gateway_request.status = 'success'
                result = {
                    'success': True,
                    'request_id': request_id,
                    'gateway_response': gateway_request.response_data,
                    'processing_time_ms': processing_time
                }
            else:
                gateway_request.status = 'failed'
                result = {
                    'success': False,
                    'request_id': request_id,
                    'error': f"Payment failed: {response.status_code}",
                    'gateway_response': gateway_request.response_data
                }

            gateway_request.save()
            return result

        except Exception as e:
            logger.error(f"Payment processing error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'request_id': request_id if 'request_id' in locals() else None
            }

    def query_payment(self, transaction_reference: str) -> Dict:
        """Query payment status"""

        try:
            # Prepare headers
            headers = {
                'Content-Type': 'application/json'
            }

            # Add authentication
            if self.gateway.auth_type == 'jwt':
                token = self.get_valid_token()
                if not token:
                    raise Exception("Failed to obtain valid token")
                headers['Authorization'] = f'Bearer {token}'

            # Query URL
            query_url = f"{self.gateway.base_url.rstrip('/')}/query/{transaction_reference}"

            response = requests.get(
                url=query_url,
                headers=headers,
                timeout=self.gateway.timeout_seconds
            )

            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f"Query failed: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Payment query error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
