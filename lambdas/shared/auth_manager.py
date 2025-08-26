"""
Authentication Manager for AI Assistant
Handles API keys and credentials from AWS Secrets Manager
"""

import json
import logging
import os
import boto3
from typing import Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

class AuthManager:
    """Manages authentication for various APIs"""
    
    def __init__(self):
        self.secrets_client = boto3.client('secretsmanager')
        self._cached_secrets = {}
    
    def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """Retrieve a secret from AWS Secrets Manager"""
        try:
            if secret_name in self._cached_secrets:
                return self._cached_secrets[secret_name]
            
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            secret_data = json.loads(response['SecretString'])
            self._cached_secrets[secret_name] = secret_data
            
            logger.info(f"Successfully retrieved secret: {secret_name}")
            return secret_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise
    
    def get_google_calendar_credentials(self) -> Credentials:
        """Get Google Calendar credentials"""
        try:
            secret_name = os.environ.get('GOOGLE_CREDENTIALS_SECRET', 'google-calendar-credentials')
            creds_data = self.get_secret(secret_name)
            
            # Create credentials object
            creds = Credentials(
                token=creds_data.get('token'),
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=creds_data.get('client_id'),
                client_secret=creds_data.get('client_secret'),
                scopes=['https://www.googleapis.com/auth/calendar.readonly']
            )
            
            # Refresh token if needed
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("Refreshed Google Calendar access token")
                
                # TODO: Update the secret with new token
                # self._update_google_token(secret_name, creds.token)
            
            return creds
            
        except Exception as e:
            logger.error(f"Failed to get Google Calendar credentials: {e}")
            raise
    
    def get_openai_api_key(self) -> str:
        """Get OpenAI API key"""
        try:
            secret_name = os.environ.get('OPENAI_API_KEY_SECRET', 'openai-api-key')
            secret_data = self.get_secret(secret_name)
            return secret_data.get('api_key') or secret_data.get('OPENAI_API_KEY')
            
        except Exception as e:
            logger.error(f"Failed to get OpenAI API key: {e}")
            raise
    
    def get_telegram_bot_token(self) -> str:
        """Get Telegram Bot token"""
        try:
            secret_name = os.environ.get('TELEGRAM_BOT_TOKEN_SECRET', 'telegram-bot-token')
            secret_data = self.get_secret(secret_name)
            return secret_data.get('bot_token') or secret_data.get('BOT_TOKEN')
            
        except Exception as e:
            logger.error(f"Failed to get Telegram Bot token: {e}")
            raise
    
    def _update_google_token(self, secret_name: str, new_token: str) -> None:
        """Update Google Calendar token in Secrets Manager"""
        try:
            # Get current secret
            current_secret = self.get_secret(secret_name)
            current_secret['token'] = new_token
            
            # Update the secret
            self.secrets_client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(current_secret)
            )
            
            # Update cache
            self._cached_secrets[secret_name] = current_secret
            
            logger.info("Updated Google Calendar token in Secrets Manager")
            
        except Exception as e:
            logger.error(f"Failed to update Google Calendar token: {e}")
            # Don't raise - this is not critical for operation
    
    def validate_credentials(self) -> Dict[str, bool]:
        """Validate all required credentials"""
        validation_results = {}
        
        try:
            # Test Google Calendar credentials
            creds = self.get_google_calendar_credentials()
            validation_results['google_calendar'] = creds.valid
        except Exception:
            validation_results['google_calendar'] = False
        
        try:
            # Test OpenAI API key
            api_key = self.get_openai_api_key()
            validation_results['openai'] = bool(api_key and len(api_key) > 10)
        except Exception:
            validation_results['openai'] = False
        
        try:
            # Test Telegram Bot token
            bot_token = self.get_telegram_bot_token()
            validation_results['telegram_bot'] = bool(bot_token and len(bot_token) > 10)
        except Exception:
            validation_results['telegram_bot'] = False
        
        return validation_results

# Global instance
auth_manager = AuthManager()
