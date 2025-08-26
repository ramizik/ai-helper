import json
import logging
import os
from typing import Dict, Any, List
import boto3
import requests
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')

def get_bot_token() -> str:
    """Retrieve bot token from AWS Secrets Manager"""
    try:
        secret_name = os.environ.get('BOT_TOKEN_SECRET')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])
        return secret_data.get('bot_token', '')
    except Exception as e:
        logger.error(f"Failed to retrieve bot token: {e}")
        return ""

def get_pending_notifications() -> List[Dict[str, Any]]:
    """Get all pending notifications that are due to be sent"""
    try:
        table_name = os.environ.get('NOTIFICATIONS_TABLE', 'aihelper-notifications-dev')
        table = dynamodb.Table(table_name)
        
        now = datetime.utcnow().isoformat()
        
        # Query for notifications that are due
        response = table.query(
            IndexName='UserTimeIndex',
            KeyConditionExpression='scheduled_time <= :now',
            FilterExpression='#status = :status',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':now': now,
                ':status': 'pending'
            }
        )
        
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"Failed to get pending notifications: {e}")
        return []

def send_telegram_message(user_id: int, message: str) -> bool:
    """Send a message to a user via Telegram Bot API"""
    try:
        bot_token = get_bot_token()
        if not bot_token:
            logger.error("Bot token not available")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': user_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.info(f"Message sent successfully to user {user_id}")
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description')}")
                return False
        else:
            logger.error(f"HTTP error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

def update_notification_status(notification_id: str, status: str, sent_at: str = None) -> bool:
    """Update notification status in DynamoDB"""
    try:
        table_name = os.environ.get('NOTIFICATIONS_TABLE', 'aihelper-notifications-dev')
        table = dynamodb.Table(table_name)
        
        update_expression = "SET #status = :status"
        expression_attributes = {
            '#status': 'status'
        }
        expression_values = {
            ':status': status
        }
        
        if sent_at:
            update_expression += ", sent_at = :sent_at"
            expression_attributes['#sent_at'] = 'sent_at'
            expression_values[':sent_at'] = sent_at
        
        table.update_item(
            Key={'notification_id': notification_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attributes,
            ExpressionAttributeValues=expression_values
        )
        
        logger.info(f"Updated notification {notification_id} status to {status}")
        return True
    except Exception as e:
        logger.error(f"Failed to update notification status: {e}")
        return False

def process_notifications() -> Dict[str, Any]:
    """Process all pending notifications"""
    try:
        notifications = get_pending_notifications()
        logger.info(f"Found {len(notifications)} pending notifications")
        
        success_count = 0
        failure_count = 0
        
        for notification in notifications:
            try:
                user_id = notification.get('user_id')
                content = notification.get('content', '')
                notification_id = notification.get('notification_id')
                
                if not user_id or not content:
                    logger.warning(f"Invalid notification data: {notification}")
                    continue
                
                # Send the notification
                if send_telegram_message(user_id, content):
                    # Mark as sent
                    update_notification_status(
                        notification_id, 
                        'sent', 
                        datetime.utcnow().isoformat()
                    )
                    success_count += 1
                else:
                    # Mark as failed
                    update_notification_status(notification_id, 'failed')
                    failure_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing notification {notification.get('notification_id')}: {e}")
                failure_count += 1
        
        return {
            'total': len(notifications),
            'success': success_count,
            'failure': failure_count
        }
        
    except Exception as e:
        logger.error(f"Error processing notifications: {e}")
        return {
            'total': 0,
            'success': 0,
            'failure': 1
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for sending notifications"""
    try:
        logger.info(f"Notifier received event: {json.dumps(event)}")
        
        # Process all pending notifications
        result = process_notifications()
        
        logger.info(f"Notification processing completed: {result}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'result': result
            })
        }
        
    except Exception as e:
        logger.error(f"Notifier error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
