"""
Database Models for AI Assistant
Defines DynamoDB table schemas and data structures
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import json

class UserPreferences(BaseModel):
    """User preferences for notifications and scheduling"""
    morning_summary_time: str = Field(default="08:00", description="Time for daily summary")
    reminder_frequency: int = Field(default=30, description="Reminder frequency in minutes")
    notification_types: List[str] = Field(default=["events", "tasks"], description="Types of notifications to receive")
    timezone: str = Field(default="America/Los_Angeles", description="User's timezone")

class UserProfile(BaseModel):
    """User profile information"""
    user_id: int = Field(..., description="Telegram user ID")
    first_name: str = Field(..., description="User's first name")
    username: Optional[str] = Field(None, description="Telegram username")
    timezone: str = Field(default="America/Los_Angeles")
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')

class CalendarEvent(BaseModel):
    """Calendar event structure"""
    user_id: int = Field(..., description="User ID")
    sort_key: str = Field(..., description="DynamoDB sort key")
    event_id: str = Field(..., description="Google Calendar event ID")
    title: str = Field(..., description="Event title")
    description: str = Field(default="", description="Event description")
    start_time: str = Field(..., description="Event start time (ISO format)")
    end_time: str = Field(..., description="Event end time (ISO format)")
    location: str = Field(default="", description="Event location")
    attendees: List[Dict[str, str]] = Field(default_factory=list, description="Event attendees")
    all_day: bool = Field(default=False, description="Whether event is all-day")
    ai_processed: bool = Field(default=False, description="Whether AI has processed this event")
    reminder_sent: bool = Field(default=False, description="Whether reminder has been sent")
    sync_time: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    raw_event: Optional[str] = Field(None, description="Original Google Calendar event data")

class AIMemory(BaseModel):
    """AI memory and context storage"""
    user_id: int = Field(..., description="User ID")
    sort_key: str = Field(..., description="DynamoDB sort key")
    context_type: str = Field(..., description="Type of memory (daily_summary, event_analysis, etc.)")
    content: Dict[str, Any] = Field(..., description="Memory content")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for semantic search")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    ttl: Optional[int] = Field(None, description="Time to live in seconds")

class Notification(BaseModel):
    """Notification record"""
    user_id: int = Field(..., description="User ID")
    sort_key: str = Field(..., description="DynamoDB sort key")
    type: str = Field(..., description="Notification type (event_reminder, daily_summary, etc.)")
    message: str = Field(..., description="Notification message")
    sent_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    status: str = Field(default="pending", description="Notification status")
    related_event_id: Optional[str] = Field(None, description="Related calendar event ID")

class DynamoDBTable:
    """DynamoDB table definitions"""
    
    @staticmethod
    def get_users_table_schema() -> Dict[str, Any]:
        """Get Users table schema for SAM template"""
        return {
            "TableName": "aihelper-users",
            "BillingMode": "PAY_PER_REQUEST",
            "AttributeDefinitions": [
                {"AttributeName": "user_id", "AttributeType": "N"},
                {"AttributeName": "sort_key", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "sort_key", "KeyType": "RANGE"}
            ]
        }
    
    @staticmethod
    def get_calendar_events_table_schema() -> Dict[str, Any]:
        """Get Calendar Events table schema for SAM template"""
        return {
            "TableName": "aihelper-calendar-events",
            "BillingMode": "PAY_PER_REQUEST",
            "AttributeDefinitions": [
                {"AttributeName": "user_id", "AttributeType": "N"},
                {"AttributeName": "sort_key", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "sort_key", "KeyType": "RANGE"}
            ]
        }
    
    @staticmethod
    def get_ai_memory_table_schema() -> Dict[str, Any]:
        """Get AI Memory table schema for SAM template"""
        return {
            "TableName": "aihelper-ai-memory",
            "BillingMode": "PAY_PER_REQUEST",
            "AttributeDefinitions": [
                {"AttributeName": "user_id", "AttributeType": "N"},
                {"AttributeName": "sort_key", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "sort_key", "KeyType": "RANGE"}
            ],
            "TimeToLiveSpecification": {
                "AttributeName": "ttl",
                "Enabled": True
            }
        }
    
    @staticmethod
    def get_notifications_table_schema() -> Dict[str, Any]:
        """Get Notifications table schema for SAM template"""
        return {
            "TableName": "aihelper-notifications",
            "BillingMode": "PAY_PER_REQUEST",
            "AttributeDefinitions": [
                {"AttributeName": "user_id", "AttributeType": "N"},
                {"AttributeName": "sort_key", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "sort_key", "KeyType": "RANGE"}
            ]
        }

# Utility functions for DynamoDB operations
def create_sort_key(prefix: str, identifier: str, timestamp: Optional[str] = None) -> str:
    """Create a sort key for DynamoDB"""
    if timestamp:
        return f"{prefix}_{timestamp}_{identifier}"
    return f"{prefix}_{identifier}"

def parse_sort_key(sort_key: str) -> Dict[str, str]:
    """Parse a sort key to extract components"""
    parts = sort_key.split('_', 2)
    if len(parts) >= 3:
        return {
            "prefix": parts[0],
            "timestamp": parts[1],
            "identifier": parts[2]
        }
    elif len(parts) == 2:
        return {
            "prefix": parts[0],
            "identifier": parts[1]
        }
    return {"prefix": sort_key}
