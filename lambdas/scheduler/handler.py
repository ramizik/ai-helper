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

def get_tasks_table_name() -> str:
    """Get the tasks table name from environment variables"""
    return os.environ.get('TASKS_TABLE', 'aihelper-tasks-dev')

def get_user_tasks(user_id: int) -> Dict[str, List[Dict[str, Any]]]:
    """Get user's tasks: due today and incomplete"""
    try:
        logger.info(f"🆕 NEW DEPLOYMENT DETECTED! get_user_tasks called for user {user_id}")
        
        table_name = get_tasks_table_name()
        logger.info(f"📋 Using tasks table: {table_name}")
        table = dynamodb.Table(table_name)
        
        # Get all user's tasks
        logger.info(f"🔍 Querying DynamoDB for user {user_id} tasks...")
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id) &
                                  boto3.dynamodb.conditions.Key('sort_key').begins_with('task#')
        )
        
        tasks = response.get('Items', [])
        logger.info(f"📊 Raw tasks from DynamoDB: {len(tasks)} items")
        
        cleaned_tasks = []
        
        # Clean task data and filter by status
        for task in tasks:
            cleaned_task = clean_event_data(task)
            if cleaned_task.get('status') != 'complete':
                cleaned_tasks.append(cleaned_task)
                logger.info(f"📋 Found incomplete task: {cleaned_task.get('name', 'Unnamed')} (status: {cleaned_task.get('status')})")
        
        logger.info(f"📝 Cleaned incomplete tasks: {len(cleaned_tasks)} items")
        
        # Separate tasks by due date
        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        logger.info(f"📅 Today's date: {today_str}")
        due_today = []
        incomplete = []
        
        for task in cleaned_tasks:
            task_due_date = task.get('due_date', '')
            logger.info(f"📋 Task {task.get('name', 'Unnamed')} due date: '{task_due_date}' (comparing with '{today_str}')")
            if task_due_date == today_str:
                due_today.append(task)
                logger.info(f"🚨 Task due today: {task.get('name', 'Unnamed')}")
            incomplete.append(task)
        
        logger.info(f"🚨 Tasks due today: {len(due_today)}")
        logger.info(f"📝 Total incomplete tasks: {len(incomplete)}")
        
        # Sort by priority (desc) then by due date
        def sort_tasks(task_list):
            return sorted(task_list, key=lambda t: (-(t.get('priority') or -1), t.get('due_date') or '9999-12-31'))
        
        result = {
            'due_today': sort_tasks(due_today),
            'incomplete': sort_tasks(incomplete)
        }
        
        logger.info(f"📋 Returning tasks result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"🆕 NEW DEPLOYMENT DETECTED! Failed to get tasks for user {user_id}: {e}")
        import traceback
        logger.error(f"📋 Task fetching error traceback: {traceback.format_exc()}")
        return {'due_today': [], 'incomplete': []}

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
            logger.info(f"👤 User: {cleaned_user.get('first_name', 'Unknown')}")
        
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
        
        # Create a time window: from current time until end of day (23:59:59)
        # This ensures we catch events that started earlier and are still running, plus all upcoming events
        time_min = (now - timedelta(hours=1)).isoformat() + 'Z'
        
        # Set time_max to end of current day
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        time_max = end_of_day.isoformat() + 'Z'
        
        logger.info(f"⏰ Checking for events in time window: {time_min} to {time_max}")
        logger.info(f"🕐 Current time: {now.isoformat() + 'Z'}")
        logger.info(f"🌙 End of day: {end_of_day.isoformat() + 'Z'}")
        
        # Fetch events from ALL calendars
        all_events = []
        for calendar_id in calendar_ids:
            try:
                logger.info(f"🔍 Checking calendar: {calendar_id}")
                events_result = service.events().list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=50,  # Increased to get more events across the day
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
        next_event = None
        next_event_start = None
        
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
                
                # Check if this is the next upcoming event (starts after current time)
                if start_dt > now:
                    if next_event is None or start_dt < next_event_start:
                        next_event = event
                        next_event_start = start_dt
                        logger.info(f"⏭️ Found next upcoming event: {event.get('summary', 'No Title')} at {start_dt}")
                        
            except Exception as e:
                logger.warning(f"Failed to parse event time: {e}")
                continue
        
        # Log summary of what we found
        if current_event:
            logger.info(f"✅ Current event: {current_event.get('summary', 'No Title')}")
        else:
            logger.info(f"😴 No current event found")
            
        if next_event:
            logger.info(f"⏭️ Next event: {next_event.get('summary', 'No Title')} at {next_event_start}")
        else:
            logger.info(f"📭 No next event found for today")
        
        if not current_event:
            logger.info(f"😴 No currently active events found for user {user_id}")
            
            # Even if no current event, return next event info if available
            if next_event and next_event_start:
                logger.info(f"📋 Returning next event info for user {user_id}")
                return {
                    'summary': 'No Current Event',
                    'start_time': '',
                    'end_time': '',
                    'location': '',
                    'description': '',
                    'event_id': '',
                    'status': 'no_current',
                    'next_event': {
                        'summary': next_event.get('summary', 'No Title'),
                        'start_time': next_event.get('start', {}).get('dateTime', ''),
                        'end_time': next_event.get('end', {}).get('dateTime', ''),
                        'location': next_event.get('location', ''),
                        'time_until_start': (next_event_start - now).total_seconds()
                    }
                }
            
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
        
        # Add next event information if available
        if next_event and next_event_start:
            next_event_end = next_event.get('end', {}).get('dateTime', '')
            formatted_event['next_event'] = {
                'summary': next_event.get('summary', 'No Title'),
                'start_time': next_event.get('start', {}).get('dateTime', ''),
                'end_time': next_event_end,
                'location': next_event.get('location', ''),
                'time_until_start': (next_event_start - now).total_seconds()
            }
            logger.info(f"📋 Next event info added: {next_event.get('summary', 'No Title')} in {formatted_event['next_event']['time_until_start']:.0f} seconds")
        
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

def add_task_reminders(user_id: int, context: str) -> str:
    """Add task reminders to messages based on context"""
    try:
        logger.info(f"🆕 NEW DEPLOYMENT DETECTED! add_task_reminders called for user {user_id}, context: {context}")
        
        user_tasks = get_user_tasks(user_id)
        logger.info(f"📊 User tasks retrieved: {user_tasks}")
        
        due_today = user_tasks.get('due_today', [])
        incomplete = user_tasks.get('incomplete', [])
        
        logger.info(f"📅 Tasks due today: {len(due_today)}")
        logger.info(f"📝 Total incomplete tasks: {len(incomplete)}")
        
        if not due_today and not incomplete:
            logger.info("ℹ️ No tasks to display")
            return ""
        
        message = "\n📋 **Task Reminders**\n\n"
        
        # Add context-specific message
        if context == "free_time":
            message += "Since you're free right now, here are your tasks:\n\n"
        elif context == "after_event":
            message += "After this event, you can focus on these tasks:\n\n"
        else:
            message += "Here are your current tasks:\n\n"
        
        # Tasks due today (high priority)
        if due_today:
            message += "🚨 **Due Today:**\n"
            for i, task in enumerate(due_today[:3], 1):  # Show first 3
                priority = task.get('priority', -1)
                priority_text = f"P{priority}" if priority in (1,2,3,4,5) else "P-"
                task_name = task.get('name', 'Unnamed')
                message += f"{i}. [{priority_text}] {task_name}\n"
                logger.info(f"📋 Added due today task: [{priority_text}] {task_name}")
            
            if len(due_today) > 3:
                message += f"   ... and {len(due_today) - 3} more due today\n"
            message += "\n"
        
        # Other incomplete tasks
        if incomplete and len(incomplete) > len(due_today):
            other_tasks = [t for t in incomplete if t not in due_today]
            if other_tasks:
                message += "📝 **Other Incomplete Tasks:**\n"
                for i, task in enumerate(other_tasks[:2], 1):  # Show first 2
                    priority = task.get('priority', -1)
                    priority_text = f"P{priority}" if priority in (1,2,3,4,5) else "P-"
                    due_date = task.get('due_date', '')
                    due_text = f" (due: {due_date})" if due_date else ""
                    task_name = task.get('name', 'Unnamed')
                    message += f"{i}. [{priority_text}] {task_name}{due_text}\n"
                    logger.info(f"📋 Added incomplete task: [{priority_text}] {task_name}{due_text}")
                
                if len(other_tasks) > 2:
                    message += f"   ... and {len(other_tasks) - 2} more incomplete tasks\n"
                message += "\n"
        
        message += "💡 Use `/t-list` to see all your tasks or `/t-today` for today's due tasks."
        logger.info(f"📋 Final task reminder message length: {len(message)} characters")
        return message
        
    except Exception as e:
        logger.error(f"🆕 NEW DEPLOYMENT DETECTED! Failed to add task reminders: {e}")
        import traceback
        logger.error(f"📋 Task reminder error traceback: {traceback.format_exc()}")
        return "\n📋 **Tasks**\nUnable to load task information at this time.\n"

def format_current_event_message(event: Optional[Dict[str, Any]], user_name: str, user_id: int) -> str:
    """Format current event into a readable message with task reminders when appropriate"""
    logger.info(f"🆕 NEW DEPLOYMENT DETECTED! format_current_event_message called for user {user_id}, event: {event is not None}")
    
    if not event:
        # No current event - add task reminders
        message = (
            f"👋 Hello {user_name}!\n\n"
            "📅 **Current Status**\n"
            "No events scheduled for right now.\n\n"
        )
        
        # Add task reminders since user is free
        logger.info(f"🆕 NEW DEPLOYMENT DETECTED! No current event, adding free time task reminders")
        message += add_task_reminders(user_id, "free_time")
        return message
    
    # Check if this is a "no current event" case with next event info
    if event.get('status') == 'no_current':
        next_event = event.get('next_event')
        if next_event:
            next_summary = next_event.get('summary', 'No Title')
            next_location = next_event.get('location', '')
            time_until_start = next_event.get('time_until_start', 0)
            
            # Format time until next event
            if time_until_start > 0:
                hours = int(time_until_start // 3600)
                minutes = int((time_until_start % 3600) // 60)
                
                if hours > 0:
                    time_str = f"{hours}h {minutes}m"
                else:
                    time_str = f"{minutes}m"
                
                message = f"👋 Hello {user_name}!\n\n"
                message += "📅 **Current Status**\n"
                message += "No events scheduled for right now.\n\n"
                message += "⏭️ **Next Upcoming Event**\n\n"
                message += f"**{next_summary}**\n"
                message += f"⏰ Starts in: **{time_str}**\n"
                
                # Add start and end times
                try:
                    if 'T' in next_event.get('start_time', ''):
                        start_dt = datetime.fromisoformat(next_event.get('start_time', '').replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(next_event.get('end_time', '').replace('Z', '+00:00'))
                        start_time_str = start_dt.strftime('%I:%M %p')
                        end_time_str = end_dt.strftime('%I:%M %p')
                        message += f"🕐 **{start_time_str} - {end_time_str}**\n"
                except:
                    message += f"🕐 Time: TBD\n"
                
                if next_location:
                    message += f"📍 {next_location}\n"
                    
                message += "\n"
                message += "You have some free time! 🚀"
                return message
    
    # Check if there's a next event - if no next event, add task reminders
    next_event = event.get('next_event')
    has_next_event = next_event and next_event.get('summary')
    
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
    message += f"🕐 {start_time_str} - {end_time_str}\n"
    
    if location:
        message += f"📍 {location}\n"
    
    message += "\n"
    
    # Add next event information if available
    next_event = event.get('next_event')
    if next_event:
        next_summary = next_event.get('summary', 'No Title')
        next_location = next_event.get('location', '')
        next_start_time = next_event.get('start_time', '')
        next_end_time = next_event.get('end_time', '')
        time_until_start = next_event.get('time_until_start', 0)
        
        # Format time until next event
        if time_until_start > 0:
            hours = int(time_until_start // 3600)
            minutes = int((time_until_start % 3600) // 60)
            
            if hours > 0:
                time_str = f"{hours}h {minutes}m"
            else:
                time_str = f"{minutes}m"
            
            message += "⏭️ **Next Upcoming Event**\n\n"
            message += f"**{next_summary}**\n"
            message += f"⏰ Starts in: **{time_str}**\n"
            
            # Add start and end times
            try:
                if 'T' in next_start_time:
                    start_dt = datetime.fromisoformat(next_start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(next_end_time.replace('Z', '+00:00'))
                    start_time_str = start_dt.strftime('%I:%M %p')
                    end_time_str = end_dt.strftime('%I:%M %p')
                    message += f"🕐 **{start_time_str} - {end_time_str}**\n"
            except:
                message += f"🕐 Time: TBD\n"
            
            if next_location:
                message += f"📍 {next_location}\n"
                
            message += "\n"
        else:
            message += "⏭️ **Next Upcoming Event**\n\n"
            message += f"**{next_summary}**\n"
            message += "⏰ Starting soon!\n"
            
            # Add start and end times
            try:
                if 'T' in next_start_time:
                    start_dt = datetime.fromisoformat(next_start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(next_end_time.replace('Z', '+00:00'))
                    start_time_str = start_dt.strftime('%I:%M %p')
                    end_time_str = end_dt.strftime('%I:%M %p')
                    message += f"🕐 **{start_time_str} - {end_time_str}**\n"
            except:
                message += f"🕐 Time: TBD\n"
            
            if next_location:
                message += f"📍 {next_location}\n"
                
            message += "\n"
    
    # ALWAYS add task reminders regardless of next event status
    logger.info(f"🆕 NEW DEPLOYMENT DETECTED! Adding task reminders for user {user_id} (always)")
    task_reminders = add_task_reminders(user_id, "after_event")
    logger.info(f"📋 Task reminders generated: {len(task_reminders)} characters")
    if task_reminders:
        logger.info(f"📋 Task reminder preview: {task_reminders[:100]}...")
    message += task_reminders
    
    message += "Stay focused and productive! 💪"
    logger.info(f"🆕 NEW DEPLOYMENT DETECTED! Final message length: {len(message)} characters")
    return message

def format_morning_summary_message(events: List[Dict[str, Any]], user_name: str, user_id: int) -> str:
    """Format today's events into a morning summary message with task information"""
    if not events:
        message = (
            f"🌅 Good morning {user_name}!\n\n"
            "📅 **Your Schedule Today**\n"
            "No events scheduled for today.\n\n"
        )
    else:
        # Sort events by start time
        sorted_events = sorted(events, key=lambda x: x.get('start_time', ''))
        
        # Get today's date for the header
        today = datetime.utcnow()
        today_str = today.strftime('%A, %B %d, %Y')
        
        message = f"🌅 Good morning {user_name}!\n\n"
        message += f"📅 **Your Schedule for {today_str}**\n\n"
        
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
                    time_icon = "🕐"
                else:
                    # Date event (all-day)
                    start_dt = datetime.fromisoformat(start_time)
                    start_time_str = "All Day"
                    end_time_str = "All Day"
                    time_icon = "📅"
            except:
                start_time_str = "Time TBD"
                end_time_str = "Time TBD"
                time_icon = "❓"
            
            message += f"{i}. **{summary}**\n"
            message += f"   {time_icon} {start_time_str} - {end_time_str}\n"
            
            if location:
                message += f"   📍 {location}\n"
            
            message += "\n"
        
        message += f"Total: {len(events)} event{'s' if len(events) != 1 else ''} today\n\n"
    
    # Add task information
    try:
        user_tasks = get_user_tasks(user_id)
        due_today = user_tasks.get('due_today', [])
        incomplete = user_tasks.get('incomplete', [])
        
        # Tasks due today section
        message += "📋 **Tasks Due Today**\n"
        if due_today:
            for i, task in enumerate(due_today, 1):
                priority = task.get('priority', -1)
                priority_text = f"P{priority}" if priority in (1,2,3,4,5) else "P-"
                message += f"{i}. [{priority_text}] {task.get('name', 'Unnamed')}\n"
            message += f"\nYou have {len(due_today)} task{'s' if len(due_today) != 1 else ''} due today!\n\n"
        else:
            message += "No tasks due today. 🎉\n\n"
        
        # All incomplete tasks section
        message += "📝 **All Incomplete Tasks**\n"
        if incomplete:
            for i, task in enumerate(incomplete[:5], 1):  # Show first 5
                priority = task.get('priority', -1)
                priority_text = f"P{priority}" if priority in (1,2,3,4,5) else "P-"
                due_date = task.get('due_date', '')
                due_text = f" (due: {due_date})" if due_date else ""
                message += f"{i}. [{priority_text}] {task.get('name', 'Unnamed')}{due_text}\n"
            
            if len(incomplete) > 5:
                message += f"... and {len(incomplete) - 5} more incomplete tasks\n"
            
            message += f"\nYou have {len(incomplete)} incomplete task{'s' if len(incomplete) != 1 else ''} in total.\n\n"
        else:
            message += "All tasks completed! 🎉\n\n"
        
    except Exception as e:
        logger.error(f"Failed to add task information to morning summary: {e}")
        message += "📋 **Tasks**\nUnable to load task information at this time.\n\n"
    
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
            message = format_morning_summary_message(todays_events, user_name, user_id)
            event_count = len(todays_events)
            notification_type = 'morning_summary'
            events_found = len(todays_events)
        else:
            # Get current event for regular reminders
            current_event = get_current_event_from_google(user_id)
            # Clean event data to remove Decimal types
            if current_event:
                current_event = clean_event_data(current_event)
            message = format_current_event_message(current_event, user_name, user_id)
            event_count = 1 if current_event else 0
            notification_type = 'current_event_reminder'
            events_found = current_event is not None
        
        # Log the final message before sending
        logger.info(f"🆕 NEW DEPLOYMENT DETECTED! Final message before sending (first 200 chars): {message[:200]}...")
        logger.info(f"🆕 NEW DEPLOYMENT DETECTED! Message length: {len(message)} characters")
        
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
