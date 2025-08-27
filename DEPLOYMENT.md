# 🚀 AI Assistant AWS Deployment Guide

## Quick Start

### 1. Prerequisites
- AWS CLI installed and configured
- AWS SAM CLI installed
- Docker installed (for automatic dependency management)

### 2. Deploy to AWS
```powershell
# Navigate to project directory
cd C:\Users\ramis\OneDrive\Desktop\Programming\ai-helper\ai-helper

# Deploy to development environment
.\infrastructure\scripts\deploy.ps1 -Environment dev

# Deploy to production environment
.\infrastructure\scripts\deploy.ps1 -Environment prod
```

### 3. What Gets Deployed
- **2 Lambda Functions**: Telegram Bot (working) + Calendar Fetcher (working)
- **2 DynamoDB Tables**: Users + Calendar Events
- **1 EventBridge Rule**: Hourly calendar sync
- **2 Secrets Manager Secrets**: Google Calendar + Telegram Bot Token
- **1 API Gateway**: Webhook endpoint for Telegram

## Configuration

### Environment Variables
Copy `env.template` to `.env` and fill in:
```bash
BOT_TOKEN=your_telegram_bot_token_here
```

### AWS Secrets Manager
The deployment automatically creates secrets with placeholder values. Update them with real credentials:
- `google-calendar-credentials-dev` - Google Calendar OAuth credentials
- `telegram-bot-token-dev` - Telegram Bot Token

## Architecture

This is a **fully cloud-native** AI Assistant with **working functionality only**:
- ✅ **Telegram Bot** - Fully functional webhook handler
- ✅ **Calendar Fetcher** - Working Google Calendar integration
- ❌ **No placeholder functions** - Only deployed what actually works
- ✅ **Automatic dependency management** via SAM containers
- ✅ **Event-driven calendar sync** via EventBridge
- ✅ **Secure credential storage** via Secrets Manager

## What Works After Deployment

### 1. Telegram Bot
- ✅ Responds to `/start`, `/help` commands
- ✅ Echoes user messages
- ✅ Stores user data in DynamoDB
- ✅ Webhook endpoint working

### 2. Calendar Fetcher
- ✅ Runs every hour automatically
- ✅ Connects to Google Calendar API
- ✅ Fetches real calendar events
- ✅ Stores events in DynamoDB
- ✅ Comprehensive CloudWatch logging

## Monitoring

### CloudWatch Logs
- **Telegram Bot**: `/aws/lambda/aihelper-telegram-bot-dev`
- **Calendar Fetcher**: `/aws/lambda/aihelper-calendar-fetcher-dev`

### What to Look For
- **Telegram Bot**: User interactions, command processing
- **Calendar Fetcher**: Connection tests, event fetching, storage confirmation

### DynamoDB Tables
- **Users**: `aihelper-users-dev`
- **Calendar Events**: `aihelper-calendar-events-dev`

## Testing

### 1. Test Telegram Bot
- Send `/start` to your bot
- Send any message to test echo
- Check CloudWatch logs for bot function

### 2. Test Calendar Integration
- Wait for hourly sync or trigger manually
- Check CloudWatch logs for calendar fetcher
- Verify events appear in DynamoDB

## Support

For issues or questions, check:
- CloudWatch logs for detailed error information
- AWS CloudFormation for deployment status
- PROJECT_STRUCTURE.md for detailed architecture information

## Future Development

This deployment includes only working functionality. Future features will be added incrementally:
- AI processing and LLM integration
- Scheduling and notifications
- Advanced calendar features
