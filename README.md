# AI Helper - Cloud-Native AI Assistant

A fully cloud-native AI assistant built on AWS serverless architecture, designed to provide intelligent goal tracking, calendar management, reminders, and productivity assistance through Telegram integration.

## Project Overview

This project implements a comprehensive AI assistant that operates entirely in the cloud using AWS services. The system processes messages via webhooks, manages calendar events, provides AI-powered insights, and operates autonomously with scheduled tasks and proactive notifications.

## Architecture

### Core Components

**Multi-Lambda Architecture**
- **Telegram Bot Function** - Webhook-based message processing
- **Calendar Fetcher Function** - Google Calendar integration and sync
- **AI Processor Function** - LangChain-powered AI processing and memory
- **Scheduler Function** - Task scheduling and notification management
- **Notifier Function** - Proactive message delivery to users

**AWS Infrastructure**
- **API Gateway** - RESTful webhook endpoint for Telegram
- **DynamoDB Tables** - Users, Calendar Events, AI Memory, Notifications
- **EventBridge Rules** - Automated scheduling (8 AM daily, 30-min intervals, hourly sync)
- **Secrets Manager** - Secure storage for API keys and credentials
- **CloudWatch** - Comprehensive logging and monitoring

## Technology Stack

### Backend Infrastructure
- **AWS Lambda** - Serverless compute (Python 3.13 runtime)
- **Amazon API Gateway** - HTTP API management
- **Amazon DynamoDB** - NoSQL database storage
- **Amazon EventBridge** - Event-driven scheduling
- **AWS Secrets Manager** - Secure credential storage
- **Amazon CloudWatch** - Logging and monitoring
- **AWS CloudFormation/SAM** - Infrastructure as Code

### AI & Integration
- **LangChain** - AI framework for intelligent processing
- **Google Calendar API** - Calendar event management
- **OpenAI API** - AI-powered insights and responses
- **python-telegram-bot** v20.6 - Telegram Bot API wrapper

### Development & Deployment
- **AWS SAM CLI** - Serverless Application Model
- **Docker** - Container-based dependency management
- **PowerShell** - Automated deployment scripting
- **Git** - Version control and collaboration

## Component Interaction

```
Telegram API ←→ API Gateway ←→ Lambda Functions ←→ AWS Services
                     ↓                           ↓
               EventBridge Rules            DynamoDB + Secrets
                     ↓                           ↓
               Scheduled Tasks              AI Processing
```

1. **Message Flow**: User sends message → Telegram → API Gateway webhook → Lambda function
2. **AI Processing**: Lambda processes with AI context → Stores in memory → Generates intelligent response
3. **Calendar Integration**: Hourly sync with Google Calendar → Store events → Schedule reminders
4. **Proactive Notifications**: EventBridge triggers → AI analysis → Send relevant updates to users
5. **Data Persistence**: All interactions stored in DynamoDB with AI memory and context

## File Structure

### Core Application
- `lambdas/telegram_bot/` - Telegram webhook handler
- `lambdas/calendar_fetcher/` - Google Calendar integration
- `lambdas/ai_processor/` - AI processing and memory management
- `lambdas/scheduler/` - Task scheduling and management
- `lambdas/notifier/` - Notification delivery system

### Infrastructure & Configuration
- `template.yaml` - AWS SAM infrastructure definition
- `infrastructure/scripts/deploy.ps1` - AWS deployment automation
- `env.template` - Environment configuration template
- `DEPLOYMENT.md` - Deployment guide and instructions

### Documentation
- `PROJECT_STRUCTURE.md` - Detailed architecture documentation
- `docs/` - Technical documentation and API references

## Current Capabilities

### Bot Commands
- **`/start`** - User registration with personalized greeting
- **`/help`** - Command assistance and bot information
- **AI Chat** - Intelligent responses with context awareness

### Autonomous Features
- **Morning Summaries** - Daily 8 AM schedule overview
- **Event Reminders** - 30-minute advance notifications
- **Calendar Sync** - Hourly Google Calendar integration
- **AI Memory** - Context-aware conversations and insights

### Infrastructure Features
- **Auto-scaling** - Handles traffic spikes automatically
- **Fault tolerance** - DynamoDB backup and Lambda retry logic
- **Security** - Encrypted credential storage and IAM-based permissions
- **Cost optimization** - Pay-per-use serverless model (~$5-20/month)

## Deployment

This is a **fully cloud-native** system with no local development files:
- No local testing scripts
- No local dependency management
- Automatic dependency installation via SAM containers
- Event-driven architecture via AWS EventBridge
- Secure credential management via AWS Secrets Manager

See `DEPLOYMENT.md` for complete deployment instructions.
