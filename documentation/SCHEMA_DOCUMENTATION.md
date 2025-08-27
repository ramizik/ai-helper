# AI Assistant - Data Schema Documentation

This document describes all data schemas used in the AI Assistant project. Update this file whenever you make changes to data structures, table schemas, or API contracts.

## 📋 **Table of Contents**

- [DynamoDB Tables](#dynamodb-tables)
- [Data Models](#data-models)
- [API Schemas](#api-schemas)
- [Environment Variables](#environment-variables)
- [Schema Evolution Rules](#schema-evolution-rules)
- [Change Log](#change-log)

---

## 🗄️ **DynamoDB Tables**

### **1. Users Table (`aihelper-users-{environment}`)**

**Purpose**: Stores user profiles, preferences, and conversation history.

**Primary Key Structure**:
- **Partition Key (HASH)**: `user_id` (Number) - Telegram user ID
- **Sort Key (RANGE)**: `sort_key` (String) - Item type identifier

**Item Types**:

#### **User Profile (`sort_key: 'profile'`)**
```json
{
  "user_id": 1681943565,
  "sort_key": "profile",
  "first_name": "John",
  "username": "john_doe",
  "created_at": "2025-08-27T04:00:00Z",
  "updated_at": "2025-08-27T04:00:00Z"
}
```

#### **Message History (`sort_key: 'message_{timestamp}_{sender}'`)**
```json
{
  "user_id": 1681943565,
  "sort_key": "message_1732646400_user",
  "message": "Hello bot!",
  "sender": "user",
  "timestamp": "2025-08-27T04:00:00Z",
  "date": "2025-08-27",
  "time": "04:00:00"
}
```

**Table Properties**:
- **Billing Mode**: PAY_PER_REQUEST
- **Point-in-Time Recovery**: Enabled
- **Streams**: NEW_AND_OLD_IMAGES

---

### **2. Calendar Events Table (`aihelper-calendar-events-{environment}`)**

**Purpose**: Stores calendar events fetched from Google Calendar API.

**Primary Key Structure**:
- **Partition Key (HASH)**: `event_id` (String) - Google Calendar event ID
- **Sort Key (RANGE)**: `start_time` (String) - Event start time (ISO format)

**Global Secondary Index**:
- **Index Name**: `UserTimeIndex`
- **Partition Key**: `user_id` (Number)
- **Sort Key**: `start_time` (String)

**Item Structure**:
```json
{
  "event_id": "abc123def456",
  "start_time": "2025-08-27T10:00:00Z",
  "user_id": 1,
  "title": "Team Meeting",
  "description": "Weekly team sync",
  "end_time": "2025-08-27T11:00:00Z",
  "location": "Conference Room A",
  "attendees": [
    {
      "email": "john@company.com",
      "status": "accepted"
    }
  ],
  "all_day": false,
  "ai_processed": false,
  "reminder_sent": false,
  "sync_time": "2025-08-27T04:00:00Z",
  "raw_event": "{...}"
}
```

**Table Properties**:
- **Billing Mode**: PAY_PER_REQUEST
- **Point-in-Time Recovery**: Enabled

---

## 🏗️ **Data Models**

### **User Profile Model**
```python
class UserProfile:
    user_id: int                    # Telegram user ID
    sort_key: str                   # Always 'profile'
    first_name: str                 # User's first name
    username: Optional[str]         # Telegram username
    created_at: str                 # ISO timestamp
    updated_at: str                 # ISO timestamp
```

### **Calendar Event Model**
```python
class CalendarEvent:
    event_id: str                   # Google Calendar event ID
    start_time: str                 # ISO timestamp
    user_id: int                    # User ID (for GSI queries)
    title: str                      # Event title
    description: str                # Event description
    end_time: str                   # ISO timestamp
    location: str                   # Event location
    attendees: List[Dict]           # List of attendee objects
    all_day: bool                   # Whether event is all-day
    ai_processed: bool              # AI processing status
    reminder_sent: bool             # Reminder notification status
    sync_time: str                  # Last sync timestamp
    raw_event: Optional[str]        # Original Google Calendar data
```

### **Message History Model**
```python
class MessageHistory:
    user_id: int                    # Telegram user ID
    sort_key: str                   # Format: 'message_{timestamp}_{sender}'
    message: str                    # Message content
    sender: str                     # 'user' or 'bot'
    timestamp: str                  # ISO timestamp
    date: str                       # YYYY-MM-DD format
    time: str                       # HH:MM:SS format
```

---

## 🔌 **API Schemas**

### **Telegram Bot Webhook**
**Endpoint**: `POST /webhook`

**Request Body**:
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 123,
    "from": {
      "id": 1681943565,
      "first_name": "John",
      "username": "john_doe"
    },
    "date": 1732646400,
    "text": "/start"
  }
}
```

**Response**:
```json
{
  "statusCode": 200,
  "body": "OK"
}
```

### **Calendar Fetcher Lambda**
**Input Event**:
```json
{
  "days_ahead": 7
}
```

**Response**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Calendar fetching completed successfully",
    "events_fetched": 8,
    "events_stored": 8,
    "user_id": 1,
    "timestamp": "2025-08-27T04:04:42.788735"
  }
}
```

---

## 🌍 **Environment Variables**

### **Telegram Bot Function**
```bash
USERS_TABLE=aihelper-users-dev
BOT_TOKEN_SECRET=telegram-bot-token-dev
ENVIRONMENT=dev
```

### **Calendar Fetcher Function**
```bash
CALENDAR_EVENTS_TABLE=aihelper-calendar-events-dev
GOOGLE_CREDENTIALS_SECRET=google-calendar-credentials-dev
ENVIRONMENT=dev
```

---

## 📈 **Schema Evolution Rules**

### **Safe Changes (No Redeployment Required)**
✅ **Adding new fields** to existing items
✅ **Modifying data types** within items
✅ **Adding new item types** with different sort keys
✅ **Changing field values** or adding optional fields

### **Changes Requiring Redeployment**
❌ **Modifying primary key structure** (HASH/RANGE keys)
❌ **Adding/removing Global Secondary Indexes**
❌ **Changing table billing mode**
❌ **Modifying table encryption settings**

### **Example of Safe Schema Evolution**
```python
# Before
user_item = {
    'user_id': user.id,
    'sort_key': 'profile',
    'first_name': user.first_name,
    'username': user.username
}

# After (safe to add)
user_item = {
    'user_id': user.id,
    'sort_key': 'profile',
    'first_name': user.first_name,
    'username': user.username,
    'email': user.email,                    # ✅ New field
    'timezone': 'America/Los_Angeles',      # ✅ New field
    'preferences': {                        # ✅ New nested field
        'notifications': True,
        'language': 'en'
    }
}
```

---

## 📝 **Change Log**

### **2025-08-27 - Initial Schema**
- ✅ **Users Table**: Basic user profile and message history
- ✅ **Calendar Events Table**: Google Calendar integration
- ✅ **Primary Keys**: Composite keys with user_id + sort_key pattern
- ✅ **GSI**: UserTimeIndex for efficient user-based queries

### **Future Changes**
- **AI Memory Storage**: For conversation context and learning
- **Notification History**: Track sent notifications
- **User Preferences**: Customizable bot behavior
- **Task Management**: To-do items and reminders

---

## 🔍 **Query Patterns**

### **Get User Profile**
```python
table.get_item(
    Key={
        'user_id': user_id,
        'sort_key': 'profile'
    }
)
```

### **Get User Messages**
```python
table.query(
    KeyConditionExpression='user_id = :uid AND begins_with(sort_key, :prefix)',
    ExpressionAttributeValues={
        ':uid': user_id,
        ':prefix': 'message_'
    }
)
```

### **Get User Calendar Events**
```python
# Using GSI
table.query(
    IndexName='UserTimeIndex',
    KeyConditionExpression='user_id = :uid AND start_time >= :start',
    ExpressionAttributeValues={
        ':uid': user_id,
        ':start': start_time
    }
)
```

---

## 📚 **References**

- [AWS DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [Google Calendar API Reference](https://developers.google.com/calendar/api/v3/reference)
- [Python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)

---

**Last Updated**: 2025-08-27  
**Version**: 1.0.0  
**Maintainer**: AI Assistant Development Team
