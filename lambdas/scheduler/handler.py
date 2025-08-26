import json
import logging
import os
from typing import Dict, Any, List
import boto3
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

def get_upcoming_events(user_id: int, hours_ahead: int = 24) -> List[Dict[str, Any]]:
    """Get upcoming calendar events for a user"""
    try:
        table_name = os.environ.get('CALENDAR_EVENTS_TABLE', 'aihelper-calendar-events-dev')
        table = dynamodb.Table(table_name)
        
        # Calculate time range
        now = datetime.utcnow()
        end_time = now + timedelta(hours=hours_ahead)
        
        # Query events in the time range
        response = table.query(
            IndexName='UserTimeIndex',
            KeyConditionExpression='user_id = :uid AND start_time BETWEEN :start AND :end',
            ExpressionAttributeValues={
                ':uid': user_id,
                ':start': now.isoformat(),
                ':end': end_time.isoformat()
            }
        )
        
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"Failed to get upcoming events: {e}")
        return []

def create_notification(user_id: int, notification_type: str, content: str, scheduled_time: datetime) -> bool:
    """Create a notification in the notifications table"""
    try:
        table_name = os.environ.get('NOTIFICATIONS_TABLE', 'aihelper-notifications-dev')
        table = dynamodb.Table(table_name)
        
        notification_data = {
            'notification_id': f"notif_{user_id}_{int(scheduled_time.timestamp())}",
            'user_id': user_id,
            'type': notification_type,
            'content': content,
            'scheduled_time': scheduled_time.isoformat(),
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat()
        }
        
        table.put_item(Item=notification_data)
        logger.info(f"Created notification: {notification_data['notification_id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        return False

def schedule_morning_summary(user_id: int) -> bool:
    """Schedule morning summary for a user"""
    try:
        # Schedule for 8 AM tomorrow
        tomorrow = datetime.utcnow() + timedelta(days=1)
        morning_time = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
        
        content = "Good morning! Here's your daily schedule and reminders."
        
        return create_notification(user_id, "morning_summary", content, morning_time)
    except Exception as e:
        logger.error(f"Failed to schedule morning summary: {e}")
        return False

def schedule_event_reminders(user_id: int, events: List[Dict[str, Any]]) -> int:
    """Schedule reminders for upcoming events"""
    try:
        reminder_count = 0
        
        for event in events:
            event_time = datetime.fromisoformat(event.get('start_time', ''))
            reminder_time = event_time - timedelta(minutes=30)  # 30 minutes before
            
            # Only schedule if reminder time is in the future
            if reminder_time > datetime.utcnow():
                content = f"Reminder: {event.get('title', 'Event')} in 30 minutes"
                if create_notification(user_id, "event_reminder", content, reminder_time):
                    reminder_count += 1
        
        logger.info(f"Scheduled {reminder_count} event reminders for user {user_id}")
        return reminder_count
    except Exception as e:
        logger.error(f"Failed to schedule event reminders: {e}")
        return 0

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for scheduling tasks"""
    try:
        logger.info(f"Scheduler received event: {json.dumps(event)}")
        
        # Extract event details
        event_type = event.get('detail-type', 'unknown')
        
        if event_type == 'regular_check':
            # This is triggered every 30 minutes
            # For now, we'll just log the check
            logger.info("Performing regular check - no specific actions needed yet")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': 'Regular check completed',
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
        
        elif event_type == 'user_specific':
            # Handle user-specific scheduling
            user_id = event.get('detail', {}).get('user_id')
            action = event.get('detail', {}).get('action')
            
            if not user_id:
                raise ValueError("User ID is required for user-specific scheduling")
            
            if action == 'schedule_morning_summary':
                success = schedule_morning_summary(user_id)
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'success': success,
                        'message': 'Morning summary scheduled' if success else 'Failed to schedule morning summary'
                    })
                }
            
            elif action == 'schedule_event_reminders':
                events = get_upcoming_events(user_id, hours_ahead=24)
                reminder_count = schedule_event_reminders(user_id, events)
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'success': True,
                        'message': f'Scheduled {reminder_count} event reminders',
                        'reminder_count': reminder_count
                    })
                }
            
            else:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'success': False,
                        'error': f'Unknown action: {action}'
                    })
                }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': f'Unknown event type: {event_type}'
                })
            }
        
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
