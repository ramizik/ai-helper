"""
Calendar Fetcher Lambda - Google Calendar Integration
Fetches user's calendar events and stores them in DynamoDB
"""

import json
import logging
import os
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Third-party imports
from googleapiclient.discovery import build
import pytz

# Local imports
import sys
sys.path.append('/opt/python/lib/site-packages')
sys.path.append('/opt/python')

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS services
dynamodb = boto3.resource('dynamodb')

def fetch_calendar_events(credentials, days_ahead: int = 7) -> List[Dict[str, Any]]:
    """Fetch calendar events from Google Calendar API"""
    try:
        # Build the Calendar service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Define time range
        now = datetime.utcnow()
        end_time = now + timedelta(days=days_ahead)
        
        # Format timestamps
        time_min = now.isoformat() + 'Z'
        time_max = end_time.isoformat() + 'Z'
        
        logger.info(f"Fetching events from {time_min} to {time_max}")
        
        # Fetch events from primary calendar
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        logger.info(f"Found {len(events)} events")
        
        return events
        
    except Exception as e:
        logger.error(f"Failed to fetch calendar events: {e}")
        raise

def store_events_in_dynamodb(events: List[Dict[str, Any]], user_id: int) -> None:
    """Store calendar events in DynamoDB"""
    try:
        table_name = os.environ.get('CALENDAR_EVENTS_TABLE', 'aihelper-calendar-events')
        table = dynamodb.Table(table_name)
        
        current_time = datetime.utcnow().isoformat() + 'Z'
        
        for event in events:
            # Extract event details
            event_id = event.get('id')
            summary = event.get('summary', 'No Title')
            description = event.get('description', '')
            location = event.get('location', '')
            
            # Handle datetime vs date events
            start = event.get('start', {})
            end = event.get('end', {})
            
            if 'dateTime' in start:
                start_time = start['dateTime']
                end_time = end['dateTime']
                all_day = False
            else:
                start_time = start.get('date', '') + 'T00:00:00Z'
                end_time = end.get('date', '') + 'T23:59:59Z'
                all_day = True
            
            # Create attendees list
            attendees = []
            for attendee in event.get('attendees', []):
                attendees.append({
                    'email': attendee.get('email', ''),
                    'status': attendee.get('responseStatus', 'needsAction')
                })
            
            # Create sort key for DynamoDB
            sort_key = f"event_{start_time}_{event_id}"
            
            # Prepare item for DynamoDB
            item = {
                'user_id': user_id,
                'sort_key': sort_key,
                'event_id': event_id,
                'title': summary,
                'description': description,
                'start_time': start_time,
                'end_time': end_time,
                'location': location,
                'attendees': attendees,
                'all_day': all_day,
                'ai_processed': False,
                'reminder_sent': False,
                'sync_time': current_time,
                'raw_event': json.dumps(event)  # Store original for debugging
            }
            
            # Store in DynamoDB
            table.put_item(Item=item)
            logger.info(f"Stored event: {summary} at {start_time}")
            
    except Exception as e:
        logger.error(f"Failed to store events in DynamoDB: {e}")
        raise

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Calendar Fetcher
    Can be triggered by EventBridge (scheduled) or manually
    """
    try:
        # Get user ID (for single user system, this can be hardcoded or from environment)
        user_id = int(os.environ.get('USER_ID', '1681943565'))  # Your Telegram user ID
        
        logger.info(f"Starting calendar fetch for user {user_id}")
        
        # Import auth manager (will be available in Lambda layer)
        try:
            from shared.auth_manager import auth_manager
            credentials = auth_manager.get_google_calendar_credentials()
        except ImportError:
            # Fallback to direct import for local testing
            from google.oauth2.credentials import Credentials
            import boto3
            secrets_client = boto3.client('secretsmanager')
            
            secret_name = os.environ.get('GOOGLE_CREDENTIALS_SECRET', 'google-calendar-credentials')
            response = secrets_client.get_secret_value(SecretId=secret_name)
            creds_data = json.loads(response['SecretString'])
            
            credentials = Credentials(
                token=creds_data.get('token'),
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data.get('token_uri'),
                client_id=creds_data.get('client_id'),
                client_secret=creds_data.get('client_secret'),
                scopes=['https://www.googleapis.com/auth/calendar.readonly']
            )
        
        # Fetch calendar events
        events = fetch_calendar_events(credentials, days_ahead=7)
        
        # Store events in DynamoDB
        store_events_in_dynamodb(events, user_id)
        
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully fetched and stored {len(events)} calendar events',
                'user_id': user_id,
                'events_count': len(events),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
        }
        
        logger.info(f"Calendar fetch completed successfully: {len(events)} events processed")
        return response
        
    except Exception as e:
        logger.error(f"Calendar fetch failed: {str(e)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
        }

# For local testing
if __name__ == "__main__":
    test_event = {}
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
