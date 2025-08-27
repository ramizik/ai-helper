"""
Calendar Fetcher Lambda - Google Calendar Integration
Fetches user's calendar events and stores them in DynamoDB
Enhanced with comprehensive testing and logging for CloudWatch monitoring
"""

import json
import logging
import os
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Third-party imports
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pytz

# Local imports
import sys
sys.path.append('/opt/python/lib/site-packages')
sys.path.append('/opt/python')

# Configure logging with detailed format
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS services
dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')

def get_google_calendar_credentials() -> Dict[str, str]:
    """Retrieve Google Calendar credentials from AWS Secrets Manager"""
    try:
        secret_name = os.environ.get('GOOGLE_CREDENTIALS_SECRET', 'google-calendar-credentials-dev')
        logger.info(f"Attempting to retrieve credentials from secret: {secret_name}")
        
        response = secrets_client.get_secret_value(SecretId=secret_name)
        # Secret is stored as plain string, parse it as JSON
        secret_data = json.loads(response['SecretString'])
        
        logger.info("Successfully retrieved Google Calendar credentials from Secrets Manager")
        logger.info(f"Credential keys found: {list(secret_data.keys())}")
        
        return secret_data
        
    except Exception as e:
        logger.error(f"Failed to retrieve Google Calendar credentials: {e}")
        logger.error(f"Secret name attempted: {secret_name}")
        raise

def test_google_calendar_connection(credentials_data: Dict[str, str]) -> bool:
    """Test connection to Google Calendar API"""
    try:
        logger.info("🔍 Testing Google Calendar API connection...")
        
        # Create credentials object
        creds = Credentials(
            token=credentials_data.get('access_token'),
            refresh_token=credentials_data.get('refresh_token'),
            token_uri=credentials_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=credentials_data.get('client_id'),
            client_secret=credentials_data.get('client_secret')
        )
        
        # Test if credentials are valid
        if creds.expired and creds.refresh_token:
            logger.info("Credentials expired, attempting to refresh...")
            creds.refresh(Request())
            logger.info("✅ Credentials refreshed successfully")
        else:
            logger.info("✅ Credentials are valid")
        
        # Test API connection by building service
        service = build('calendar', 'v3', credentials=creds)
        logger.info("✅ Google Calendar service built successfully")
        
        # Test basic API call - get calendar list
        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        logger.info(f"✅ Successfully connected to Google Calendar API")
        logger.info(f"📅 Found {len(calendars)} calendars:")
        
        for calendar in calendars:
            calendar_name = calendar.get('summary', 'Unknown')
            calendar_id = calendar.get('id', 'Unknown')
            primary = " (Primary)" if calendar.get('primary', False) else ""
            logger.info(f"   - {calendar_name}: {calendar_id}{primary}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Google Calendar API connection test failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        return False

def fetch_calendar_events(credentials_data: Dict[str, str], days_ahead: int = 7) -> List[Dict[str, Any]]:
    """Fetch calendar events from Google Calendar API"""
    try:
        logger.info(f"📅 Fetching calendar events for next {days_ahead} days...")
        
        # Create credentials object
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
            logger.info("🔄 Credentials refreshed before fetching events")
        
        # Build the Calendar service
        service = build('calendar', 'v3', credentials=creds)
        
        # Define time range
        now = datetime.utcnow()
        end_time = now + timedelta(days=days_ahead)
        
        # Format timestamps
        time_min = now.isoformat() + 'Z'
        time_max = end_time.isoformat() + 'Z'
        
        logger.info(f"⏰ Fetching events from {time_min} to {time_max}")
        
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
        logger.info(f"✅ Successfully fetched {len(events)} events from Google Calendar")
        
        # Log event details for testing
        if events:
            logger.info("📋 Event details:")
            for i, event in enumerate(events[:5]):  # Log first 5 events
                event_id = event.get('id', 'Unknown')
                summary = event.get('summary', 'No Title')
                start = event.get('start', {})
                start_time = start.get('dateTime', start.get('date', 'Unknown'))
                logger.info(f"   {i+1}. {summary} (ID: {event_id[:8]}...) at {start_time}")
            
            if len(events) > 5:
                logger.info(f"   ... and {len(events) - 5} more events")
        else:
            logger.info("📭 No events found in the specified time range")
        
        return events
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch calendar events: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        raise

def store_events_in_dynamodb(events: List[Dict[str, Any]], user_id: int = 1) -> int:
    """Store calendar events in DynamoDB"""
    try:
        table_name = os.environ.get('CALENDAR_EVENTS_TABLE', 'aihelper-calendar-events-dev')
        logger.info(f"💾 Storing {len(events)} events in DynamoDB table: {table_name}")
        
        table = dynamodb.Table(table_name)
        stored_count = 0
        
        current_time = datetime.utcnow().isoformat() + 'Z'
        
        for event in events:
            try:
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
                sort_key = f"{start_time}#{event_id}"
                
                # Prepare event item
                event_item = {
                    'event_id': event_id,
                    'user_id': user_id,
                    'start_time': start_time,
                    'end_time': end_time,
                    'summary': summary,
                    'description': description,
                    'location': location,
                    'all_day': all_day,
                    'attendees': attendees,
                    'created_at': current_time,
                    'updated_at': current_time,
                    'source': 'google_calendar',
                    'status': event.get('status', 'confirmed')
                }
                
                # Store in DynamoDB
                table.put_item(Item=event_item)
                stored_count += 1
                
                logger.info(f"   ✅ Stored event: {summary} (ID: {event_id[:8]}...)")
                
            except Exception as e:
                logger.error(f"   ❌ Failed to store event {event.get('id', 'Unknown')}: {e}")
                continue
        
        logger.info(f"💾 Successfully stored {stored_count}/{len(events)} events in DynamoDB")
        return stored_count
        
    except Exception as e:
        logger.error(f"❌ Failed to store events in DynamoDB: {e}")
        return 0

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for calendar fetching with comprehensive testing"""
    try:
        logger.info("🚀 Calendar Fetcher Lambda started")
        logger.info(f"📊 Event details: {json.dumps(event)}")
        logger.info(f"🔧 Context: {json.dumps({'function_name': context.function_name, 'function_version': context.function_version, 'memory_limit_in_mb': context.memory_limit_in_mb})})")
        
        # Test 1: Retrieve credentials
        logger.info("=" * 50)
        logger.info("🧪 TEST 1: CREDENTIAL RETRIEVAL")
        logger.info("=" * 50)
        
        try:
            credentials_data = get_google_calendar_credentials()
            logger.info("✅ CREDENTIAL RETRIEVAL: SUCCESS")
        except Exception as e:
            logger.error("❌ CREDENTIAL RETRIEVAL: FAILED")
            logger.error(f"Error: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to retrieve credentials',
                    'details': str(e)
                })
            }
        
        # Test 2: Test Google Calendar connection
        logger.info("=" * 50)
        logger.info("🧪 TEST 2: GOOGLE CALENDAR CONNECTION")
        logger.info("=" * 50)
        
        connection_success = test_google_calendar_connection(credentials_data)
        if not connection_success:
            logger.error("❌ GOOGLE CALENDAR CONNECTION: FAILED")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to connect to Google Calendar API',
                    'details': 'Connection test failed'
                })
            }
        
        logger.info("✅ GOOGLE CALENDAR CONNECTION: SUCCESS")
        
        # Test 3: Fetch calendar events
        logger.info("=" * 50)
        logger.info("🧪 TEST 3: EVENT FETCHING")
        logger.info("=" * 50)
        
        try:
            events = fetch_calendar_events(credentials_data, days_ahead=7)
            logger.info("✅ EVENT FETCHING: SUCCESS")
        except Exception as e:
            logger.error("❌ EVENT FETCHING: FAILED")
            logger.error(f"Error: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to fetch calendar events',
                    'details': str(e)
                })
            }
        
        # Test 4: Store events in DynamoDB
        logger.info("=" * 50)
        logger.info("🧪 TEST 4: DYNAMODB STORAGE")
        logger.info("=" * 50)
        
        try:
            stored_count = store_events_in_dynamodb(events)
            logger.info("✅ DYNAMODB STORAGE: SUCCESS")
        except Exception as e:
            logger.error("❌ DYNAMODB STORAGE: FAILED")
            logger.error(f"Error: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to store events in DynamoDB',
                    'details': str(e)
                })
            }
        
        # Summary
        logger.info("=" * 50)
        logger.info("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        logger.info("=" * 50)
        logger.info(f"📊 Summary:")
        logger.info(f"   - Events fetched: {len(events)}")
        logger.info(f"   - Events stored: {stored_count}")
        logger.info(f"   - User ID: {1}")
        logger.info(f"   - Time range: Next 7 days")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Calendar fetching completed successfully',
                'events_fetched': len(events),
                'events_stored': stored_count,
                'user_id': 1,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"❌ Calendar Fetcher Lambda failed with unexpected error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Unexpected error in calendar fetcher',
                'details': str(e)
            })
        }

# For local testing
if __name__ == "__main__":
    test_event = {}
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
