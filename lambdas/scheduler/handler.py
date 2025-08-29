"""
Scheduler Lambda - Automated Reminder System
Automatically sends scheduled messages to users with their upcoming calendar events
Currently set to run every minute for testing purposes
"""

import json
import logging
import os
import boto3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import pytz
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS services
dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')

def json_serializer(obj):
    """Custom JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def clean_event_data(event_data):
    """Clean event data by converting Decimal types to float"""
    if not event_data:
        return event_data
    
    cleaned = {}
    for key, value in event_data.items():
        if isinstance(value, Decimal):
            cleaned[key] = float(value)
        elif isinstance(value, dict):
            cleaned[key] = clean_event_data(value)
        elif isinstance(value, list):
            cleaned[key] = [clean_event_data(item) if isinstance(item, dict) else (float(item) if isinstance(item, Decimal) else item) for item in value]
        else:
            cleaned[key] = value
    
    return cleaned

def get_bot_token() -> str:
    """Retrieve bot token from AWS Secrets Manager"""
    try:
        secret_name = os.environ.get('BOT_TOKEN_SECRET', 'telegram-bot-token-dev')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        token = response['SecretString']
        
        if not token:
            raise ValueError("Bot token is empty")
        
        logger.info("🔑 Successfully retrieved bot token from Secrets Manager")
        return token
        
    except Exception as e:
        logger.error(f"Failed to retrieve bot token: {e}")
        raise

def get_active_users() -> List[Dict[str, Any]]:
    """Get all active users from DynamoDB"""
    try:
        logger.info(f"🆕 NEW DEPLOYMENT DETECTED! Enhanced get_active_users function")
        table_name = os.environ.get('USERS_TABLE', 'aihelper-users-dev')
        logger.info(f"🔍 Scanning table: {table_name}")
        table = dynamodb.Table(table_name)
        
        # Scan for users with profile sort keys
        response = table.scan(
            FilterExpression='begins_with(sort_key, :profile)',
            ExpressionAttributeValues={':profile': 'profile'}
        )
        
        users = response.get('Items', [])
        logger.info(f"👥 Found {len(users)} active users")
        
        # Clean user data to remove Decimal types
        cleaned_users = []
        for user in users:
            cleaned_user = clean_event_data(user)  # Reuse the same cleaning function
            cleaned_users.append(cleaned_user)
            logger.info(f"👤 User: {cleaned_user.get('user_id')} - {cleaned_user.get('first_name', 'Unknown')}")
        
        return cleaned_users
        
    except Exception as e:
        logger.error(f"Failed to get active users: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []

def get_google_calendar_credentials() -> Dict[str, str]:
    """Retrieve Google Calendar credentials from AWS Secrets Manager"""
    try:
        secret_name = os.environ.get('GOOGLE_CREDENTIALS_SECRET', 'google-calendar-credentials-dev')
        logger.info(f"🔐 Retrieving Google Calendar credentials from secret: {secret_name}")
        
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])
        
        logger.info("✅ Successfully retrieved Google Calendar credentials")
        return secret_data
        
    except Exception as e:
        logger.error(f"Failed to retrieve Google Calendar credentials: {e}")
        raise

def get_all_calendars(service) -> List[str]:
    """Get all available calendar IDs for the user"""
    try:
        logger.info("📋 Fetching all available calendars...")
        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        calendar_ids = []
        for calendar in calendars:
            calendar_id = calendar.get('id')
            calendar_name = calendar.get('summary', 'Unknown')
            primary = calendar.get('primary', False)
            access_role = calendar.get('accessRole', 'none')
            
            # Only include calendars we can read
            if access_role in ['owner', 'writer', 'reader']:
                calendar_ids.append(calendar_id)
                logger.info(f"  📅 Calendar: {calendar_name} (ID: {calendar_id}) {'[PRIMARY]' if primary else ''}")
        
        logger.info(f"✅ Found {len(calendar_ids)} accessible calendars")
        return calendar_ids
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch calendar list: {e}")
        # Fallback to primary calendar
        return ['primary']

def get_current_event_from_google(user_id: int) -> Optional[Dict[str, Any]]:
    """Get the event that is currently happening right now from Google Calendar API"""
    try:
        logger.info(f"🆕 NEW DEPLOYMENT DETECTED! Enhanced get_current_event_from_google function")
        logger.info(f"📅 Fetching current event from Google Calendar for user {user_id}")
        
        # Get Google Calendar credentials
        credentials_data = get_google_calendar_credentials()
        
        # Create credentials object
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        
        creds = Credentials(
            token=credentials_data.get('access_token'),
            refresh_token=credentials_data.get('refresh_token'),
            token_uri=credentials_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=credentials_data.get('client_id'),
            client_secret=credentials_data.get('client_secret')
        )
        
        # Refresh if needed
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logger.info("🔄 Google Calendar credentials refreshed")
        
        # Build the Calendar service
        service = build('calendar', 'v3', credentials=creds)
        
        # Get all available calendars
        calendar_ids = get_all_calendars(service)
        
        # Get current time (now)
        now = datetime.utcnow()
        
        # Create a time window: 1 hour before and 1 hour after current time
        # This ensures we catch events that started earlier and are still running
        time_min = (now - timedelta(hours=1)).isoformat() + 'Z'
        time_max = (now + timedelta(hours=1)).isoformat() + 'Z'
        
        logger.info(f"⏰ Checking for events in time window: {time_min} to {time_max}")
        logger.info(f"🕐 Current time: {now.isoformat() + 'Z'}")
        
        # Fetch events from ALL calendars
        all_events = []
        for calendar_id in calendar_ids:
            try:
                logger.info(f"🔍 Checking calendar: {calendar_id}")
                events_result = service.events().list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=20,  # Get more events per calendar
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                calendar_events = events_result.get('items', [])
                if calendar_events:
                    logger.info(f"  📊 Found {len(calendar_events)} events in calendar {calendar_id}")
                    all_events.extend(calendar_events)
                else:
                    logger.info(f"  📭 No events found in calendar {calendar_id}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch events from calendar {calendar_id}: {e}")
                continue
        
        if not all_events:
            logger.info(f"❌ No events found in any calendar for user {user_id}")
            return None
        
        logger.info(f"📊 Found {len(all_events)} total events across all calendars")
        
        # Find the event that is currently active (started before now and ends after now)
        current_event = None
        for event in all_events:
            # Check if this is an all-day event
            if event.get('start', {}).get('date') is not None:
                logger.info(f"📅 Skipping all-day event: {event.get('summary', 'No Title')}")
                continue
                
            event_start = event.get('start', {}).get('dateTime')
            event_end = event.get('end', {}).get('dateTime')
            
            # Skip events without proper start/end times
            if not event_start or not event_end:
                logger.info(f"⚠️ Skipping event without proper times: {event.get('summary', 'No Title')}")
                continue
            
            # Parse event times
            try:
                # Handle timezone-aware and naive datetime parsing
                if event_start.endswith('Z'):
                    start_dt = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
                else:
                    start_dt = datetime.fromisoformat(event_start)
                    
                if event_end.endswith('Z'):
                    end_dt = datetime.fromisoformat(event_end.replace('Z', '+00:00'))
                else:
                    end_dt = datetime.fromisoformat(event_end)
                
                # Make all datetimes timezone-aware for comparison
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)
                if now.tzinfo is None:
                    now = now.replace(tzinfo=timezone.utc)
                
                # Check if event is currently active
                if start_dt <= now <= end_dt:
                    current_event = event
                    logger.info(f"🎯 Found currently active event: {event.get('summary', 'No Title')}")
                    logger.info(f"  📅 Start: {start_dt}, End: {end_dt}, Now: {now}")
                    break
            except Exception as e:
                logger.warning(f"Failed to parse event time: {e}")
                continue
        
        if not current_event:
            logger.info(f"😴 No currently active events found for user {user_id}")
            return None
        
        # Transform Google Calendar event to our format
        formatted_event = {
            'summary': current_event.get('summary', 'No Title'),
            'start_time': current_event.get('start', {}).get('dateTime', current_event.get('start', {}).get('date', '')),
            'end_time': current_event.get('end', {}).get('dateTime', current_event.get('end', {}).get('date', '')),
            'location': current_event.get('location', ''),
            'description': current_event.get('description', ''),
            'event_id': current_event.get('id', ''),
            'status': current_event.get('status', 'confirmed')
        }
        
        return formatted_event
        
    except Exception as e:
        logger.error(f"Failed to get current event from Google Calendar for user {user_id}: {e}")
        return None

def get_todays_events_from_google(user_id: int) -> List[Dict[str, Any]]:
    """Get all events for today from Google Calendar API"""
    try:
        logger.info(f"🆕 NEW DEPLOYMENT DETECTED! Enhanced get_todays_events_from_google function")
        logger.info(f"🌅 Fetching today's events from Google Calendar for user {user_id}")
        
        # Get Google Calendar credentials
        credentials_data = get_google_calendar_credentials()
        
        # Create credentials object
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        
        creds = Credentials(
            token=credentials_data.get('access_token'),
            refresh_token=credentials_data.get('refresh_token'),
            token_uri=credentials_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=credentials_data.get('client_id'),
            client_secret=credentials_data.get('client_secret')
        )
        
        # Refresh if needed
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logger.info("Google Calendar credentials refreshed")
        
        # Build the Calendar service
        service = build('calendar', 'v3', credentials=creds)
        
        # Get all available calendars
        calendar_ids = get_all_calendars(service)
        
        # Get today's date range (start of day to end of day)
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        time_min = start_of_day.isoformat() + 'Z'
        time_max = end_of_day.isoformat() + 'Z'
        
        logger.info(f"📅 Fetching events from {time_min} to {time_max}")
        
        # Fetch all events for today from ALL calendars
        all_events = []
        for calendar_id in calendar_ids:
            try:
                logger.info(f"🔍 Checking calendar: {calendar_id}")
                events_result = service.events().list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=50,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                calendar_events = events_result.get('items', [])
                if calendar_events:
                    logger.info(f"  📊 Found {len(calendar_events)} events in calendar {calendar_id}")
                    all_events.extend(calendar_events)
                else:
                    logger.info(f"  📭 No events found in calendar {calendar_id}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch events from calendar {calendar_id}: {e}")
                continue
        
        logger.info(f"📊 Found {len(all_events)} total events across all calendars for today")
        
        # Transform Google Calendar events to our format
        formatted_events = []
        for event in all_events:
            # Check if this is an all-day event
            is_all_day = event.get('start', {}).get('date') is not None
            
            formatted_event = {
                'summary': event.get('summary', 'No Title'),
                'start_time': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
                'end_time': event.get('end', {}).get('dateTime', event.get('end', {}).get('date', '')),
                'location': event.get('location', ''),
                'description': event.get('description', ''),
                'event_id': event.get('id', ''),
                'status': event.get('status', 'confirmed'),
                'is_all_day': is_all_day
            }
            formatted_events.append(formatted_event)
            
            # Log event type for debugging
            if is_all_day:
                logger.info(f"📅 All-day event: {event.get('summary', 'No Title')}")
            else:
                logger.info(f"🕐 Time-specific event: {event.get('summary', 'No Title')}")
        
        return formatted_events
        
    except Exception as e:
        logger.error(f"Failed to get today's events from Google Calendar for user {user_id}: {e}")
        return []

def format_current_event_message(event: Optional[Dict[str, Any]], user_name: str) -> str:
    """Format current event into a readable message"""
    if not event:
        return (
            f"👋 Hello {user_name}!\n\n"
            "📅 **Current Status**\n"
            "No events scheduled for right now.\n\n"
            "You're free to work on other tasks! 🚀"
        )
    
    summary = event.get('summary', 'No Title')
    start_time = event.get('start_time', '')
    end_time = event.get('end_time', '')
    location = event.get('location', '')
    
    # Parse and format the time
    try:
        if 'T' in start_time:
            # DateTime event
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            start_time_str = start_dt.strftime('%I:%M %p')
            end_time_str = end_dt.strftime('%I:%M %p')
            date_str = start_dt.strftime('%A, %B %d')
        else:
            # Date event (all-day)
            start_dt = datetime.fromisoformat(start_time)
            start_time_str = "All Day"
            end_time_str = "All Day"
            date_str = start_dt.strftime('%A, %B %d')
    except:
        start_time_str = "Time TBD"
        end_time_str = "Time TBD"
        date_str = "Date TBD"
    
    message = f"👋 Hello {user_name}!\n\n"
    message += "📅 **Current Event**\n\n"
    message += f"**{summary}**\n"
    message += f"🕐 {start_time_str} - {end_time_str} on {date_str}\n"
    
    if location:
        message += f"📍 {location}\n"
    
    message += "\n"
    message += "Stay focused and productive! 💪"
    return message

def format_morning_summary_message(events: List[Dict[str, Any]], user_name: str) -> str:
    """Format today's events into a morning summary message"""
    if not events:
        return (
            f"🌅 Good morning {user_name}!\n\n"
            "📅 **Your Schedule Today**\n"
            "No events scheduled for today.\n\n"
            "Perfect day to plan and be productive! 🚀"
        )
    
    # Sort events by start time
    sorted_events = sorted(events, key=lambda x: x.get('start_time', ''))
    
    message = f"🌅 Good morning {user_name}!\n\n"
    message += "📅 **Your Schedule Today**\n\n"
    
    for i, event in enumerate(sorted_events, 1):
        summary = event.get('summary', 'No Title')
        start_time = event.get('start_time', '')
        end_time = event.get('end_time', '')
        location = event.get('location', '')
        
        # Parse and format the time
        try:
            if 'T' in start_time:
                # DateTime event
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                start_time_str = start_dt.strftime('%I:%M %p')
                end_time_str = end_dt.strftime('%I:%M %p')
                date_str = start_dt.strftime('%A, %B %d')
                time_icon = "🕐"
            else:
                # Date event (all-day)
                start_dt = datetime.fromisoformat(start_time)
                start_time_str = "All Day"
                end_time_str = "All Day"
                date_str = start_dt.strftime('%A, %B %d')
                time_icon = "📅"
        except:
            start_time_str = "Time TBD"
            end_time_str = "Time TBD"
            date_str = "Date TBD"
            time_icon = "❓"
        
        message += f"{i}. **{summary}**\n"
        message += f"   {time_icon} {start_time_str} - {end_time_str}\n"
        
        if location:
            message += f"   📍 {location}\n"
        
        message += "\n"
    
    message += f"Total: {len(events)} event{'s' if len(events) != 1 else ''} today\n\n"
    message += "Have a great day! 💪"
    return message

async def send_telegram_message(user_id: int, message: str) -> bool:
    """Send message to user via Telegram Bot API"""
    try:
        import httpx
        
        # Debug: Log the types of parameters
        logger.info(f"send_telegram_message called with user_id: {user_id} (type: {type(user_id)})")
        logger.info(f"message: {message[:100]}... (type: {type(message)})")
        
        bot_token = get_bot_token()
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            'chat_id': user_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        # Debug: Log the payload
        logger.info(f"Payload prepared: {payload}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info(f"Message sent successfully to user {user_id}")
                    return True
                else:
                    logger.error(f"Telegram API error for user {user_id}: {result}")
                    return False
            else:
                logger.error(f"HTTP error sending message to user {user_id}: {response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to send Telegram message to user {user_id}: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def process_user_reminders(user: Dict[str, Any], message_type: str = 'current_event') -> Dict[str, Any]:
    """Process reminders for a single user"""
    try:
        user_id = int(user.get('user_id'))  # Ensure user_id is an integer
        user_name = user.get('first_name', 'User')
        
        logger.info(f"🔄 Processing {message_type} reminders for user {user_id} ({user_name})")
        
        if message_type == 'morning_summary':
            # Get today's events for morning summary
            todays_events = get_todays_events_from_google(user_id)
            # Clean event data to remove Decimal types
            if todays_events:
                todays_events = [clean_event_data(event) for event in todays_events]
            message = format_morning_summary_message(todays_events, user_name)
            event_count = len(todays_events)
            notification_type = 'morning_summary'
            events_found = len(todays_events)
        else:
            # Get current event for regular reminders
            current_event = get_current_event_from_google(user_id)
            # Clean event data to remove Decimal types
            if current_event:
                current_event = clean_event_data(current_event)
            message = format_current_event_message(current_event, user_name)
            event_count = 1 if current_event else 0
            notification_type = 'current_event_reminder'
            events_found = current_event is not None
        
        # Send via Telegram
        success = await send_telegram_message(user_id, message)
        
        # Log the notification
        if success:
            await log_notification(user_id, notification_type, message, event_count)
            logger.info(f"📱 Telegram message sent successfully to user {user_id}")
        else:
            logger.warning(f"⚠️ Failed to send Telegram message to user {user_id}")
        
        return {
            'user_id': user_id,
            'user_name': user_name,
            'message_type': message_type,
            'events_found': events_found,
            'message_sent': success
        }
        
    except Exception as e:
        logger.error(f"Error processing {message_type} reminders for user {user.get('user_id', 'Unknown')}: {e}")
        return {
            'user_id': user.get('user_id', 'Unknown'),
            'user_name': user.get('first_name', 'Unknown'),
            'message_type': message_type,
            'error': str(e)
        }

async def log_notification(user_id: int, notification_type: str, message: str, events_count: int):
    """Log notification to DynamoDB for tracking"""
    try:
        table_name = os.environ.get('USERS_TABLE', 'aihelper-users-dev')
        table = dynamodb.Table(table_name)
        
        # Create sort key for notification
        timestamp = int(datetime.utcnow().timestamp())
        sort_key = f"notification_{timestamp}_{notification_type}"
        
        notification_item = {
            'user_id': int(user_id),  # Ensure user_id is an integer
            'sort_key': sort_key,
            'type': notification_type,
            'message': message,
            'events_count': int(events_count),  # Ensure events_count is an integer
            'sent_at': datetime.utcnow().isoformat() + 'Z',
            'status': 'sent'
        }
        
        table.put_item(Item=notification_item)
        logger.info(f"💾 Notification logged for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to log notification for user {user_id}: {e}")

async def lambda_handler_async(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Async Lambda handler for Scheduler"""
    try:
        logger.info("🚀 Scheduler Lambda started")
        logger.info(f"📊 Event details: {json.dumps(event, default=json_serializer)}")
        
        # Get all active users
        users = get_active_users()
        
        if not users:
            logger.info("No active users found")
            return {
                'statusCode': 200,
                            'body': json.dumps({
                'message': 'No active users found',
                'users_processed': 0
            }, default=json_serializer)
            }
        
        # Determine message type based on current time
        now = datetime.utcnow()
        current_hour = now.hour
        
        if current_hour == 7:  # 7 AM UTC (adjust for your timezone)
            message_type = 'morning_summary'
            logger.info("🌅 Sending morning summary messages")
        else:
            message_type = 'current_event'
            logger.info("⏰ Sending current event reminders")
        
        logger.info(f"🆕 NEW DEPLOYMENT DETECTED! Running updated scheduler code")
        logger.info(f"🚀 Version: Enhanced with emoji logging and improved event detection")
        
        # Process reminders for each user
        results = []
        for user in users:
            result = await process_user_reminders(user, message_type)
            results.append(result)
        
        # Summary
        successful_sends = sum(1 for r in results if r.get('message_sent', False))
        total_events_found = sum(r.get('events_found', 0) for r in results)
        total_users = len(users)
        
        logger.info(f"✅ Scheduler completed successfully")
        logger.info(f"📊 Summary: {successful_sends}/{total_users} messages sent, {total_events_found} events found, type: {message_type}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Scheduler completed successfully',
                'users_processed': total_users,
                'messages_sent': successful_sends,
                'total_events_found': total_events_found,
                'message_type': message_type,
                'results': results,
                'timestamp': datetime.utcnow().isoformat()
            }, default=json_serializer)
        }
        
    except Exception as e:
        logger.error(f"❌ Scheduler Lambda failed: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Scheduler failed',
                'details': str(e)
            }, default=json_serializer)
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous wrapper for AWS Lambda compatibility"""
    import asyncio
    try:
        # Create new event loop for this invocation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the async handler and get the result
        result = loop.run_until_complete(lambda_handler_async(event, context))
        
        # Clean up
        loop.close()
        
        return result
        
    except Exception as e:
        logger.error(f"Error in lambda_handler wrapper: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)}, default=json_serializer)}
    finally:
        # Ensure loop is always closed
        try:
            if 'loop' in locals() and not loop.is_closed():
                loop.close()
        except:
            pass
