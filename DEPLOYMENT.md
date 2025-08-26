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
- **5 Lambda Functions**: Telegram Bot, Calendar Fetcher, AI Processor, Scheduler, Notifier
- **4 DynamoDB Tables**: Users, Calendar Events, AI Memory, Notifications
- **3 EventBridge Rules**: Morning Summary (8 AM), Regular Check (30 min), Calendar Sync (1 hour)
- **3 Secrets Manager Secrets**: Google Calendar, OpenAI API, Telegram Bot Token
- **1 API Gateway**: Webhook endpoint for Telegram

## Configuration

### Environment Variables
Copy `env.template` to `.env` and fill in:
```bash
BOT_TOKEN=your_telegram_bot_token_here
```

### AWS Secrets Manager
The deployment automatically creates secrets with placeholder values. Update them with real credentials:
- `google-calendar-credentials-dev`
- `openai-api-key-dev`
- `telegram-bot-token-dev`

## Architecture

This is a **fully cloud-native** AI Assistant that runs entirely on AWS:
- No local development files
- No local testing scripts
- Automatic dependency management via SAM containers
- Event-driven scheduling via EventBridge
- Secure credential storage via Secrets Manager

## Monitoring

- **CloudWatch Logs**: Monitor Lambda function execution
- **CloudWatch Metrics**: Track performance and errors
- **EventBridge**: Monitor scheduled function triggers
- **DynamoDB**: Monitor data storage and access patterns

## Support

For issues or questions, check:
- CloudWatch logs for error details
- AWS CloudFormation for deployment status
- PROJECT_STRUCTURE.md for detailed architecture information
