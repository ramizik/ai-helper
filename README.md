# AI Helper - Telegram Bot

A cloud-native Telegram bot built on AWS serverless architecture, designed to evolve into a personal AI assistant for goal tracking, reminders, and productivity management.

## Project Overview

This project implements a Telegram bot that operates entirely in the cloud using AWS services. The bot processes messages via webhooks, stores user data persistently, and is designed for scalability and reliability. The architecture supports real-time message processing with comprehensive logging and monitoring.

## Architecture

### Core Components

**Telegram Bot Interface**
- Webhook-based message processing (no polling required)
- Real-time response to user commands and messages
- Handles `/start`, `/help` commands and echo functionality

**AWS Lambda Functions**
- `lambda_bot.py` - Main message processing handler
- Serverless execution with auto-scaling
- Optimized connection pooling for Lambda environment
- Async message processing with proper error handling

**API Gateway**
- RESTful webhook endpoint for Telegram
- Handles HTTPS termination and request routing
- CORS-enabled for cross-origin requests

**DynamoDB Database**
- User registration and profile storage
- Conversation history logging (planned)
- Schema: `user_id` (Hash Key) with user metadata
- Point-in-time recovery enabled

**CloudWatch Logging**
- Comprehensive request/response logging
- Error tracking and debugging information
- 14-day log retention for operational insights

## Technology Stack

### Backend Infrastructure
- **AWS Lambda** - Serverless compute (Python 3.13 runtime)
- **Amazon API Gateway** - HTTP API management
- **Amazon DynamoDB** - NoSQL database storage
- **Amazon CloudWatch** - Logging and monitoring
- **AWS CloudFormation/SAM** - Infrastructure as Code

### Bot Framework
- **python-telegram-bot** v20.6 - Telegram Bot API wrapper
- **HTTPXRequest** - Optimized HTTP client for Lambda
- **Boto3** - AWS SDK for Python integration

### Development & Deployment
- **AWS SAM CLI** - Serverless Application Model
- **PowerShell** - Automated deployment scripting
- **Git** - Version control and collaboration

## Component Interaction

```
Telegram API ←→ API Gateway ←→ Lambda Function ←→ DynamoDB
                     ↓
               CloudWatch Logs
```

1. **Message Flow**: User sends message → Telegram → API Gateway webhook → Lambda function
2. **Processing**: Lambda parses message → Routes to appropriate handler → Processes command
3. **Response**: Lambda sends reply → Telegram API → User receives response  
4. **Storage**: User data and interactions stored in DynamoDB
5. **Monitoring**: All operations logged to CloudWatch

## File Structure

### Core Application
- `lambda_bot.py` - AWS Lambda webhook handler with optimized connection management
- `telegram_bot.py` - Original local development version (polling-based)
- `template.yaml` - AWS SAM infrastructure definition

### Deployment & Configuration  
- `deploy.ps1` - Automated deployment script with environment validation
- `requirements.txt` - Python dependencies specification
- `.env` - Environment variables (BOT_TOKEN)

### Documentation
- `docs/` - Technical documentation and API references

## Current Capabilities

### Bot Commands
- **`/start`** - User registration with personalized greeting
- **`/help`** - Command assistance and bot information
- **Echo Mode** - Repeats any text message for testing

### Infrastructure Features
- **Auto-scaling** - Handles traffic spikes automatically
- **Fault tolerance** - DynamoDB backup and Lambda retry logic  
- **Security** - Encrypted token storage and IAM-based permissions
- **Cost optimization** - Pay-per-use serverless model (~$2-13/month)

## Development Approach

The project follows an **incremental development methodology**:

1. **Phase 1** ✅ - Basic bot functionality with cloud deployment
2. **Phase 2** (Planned) - AI integration for intelligent responses  
3. **Phase 3** (Planned) - Scheduled reminders and proactive messaging
4. **Phase 4** (Planned) - Calendar integration and goal tracking
5. **Phase 5** (Planned) - Advanced analytics and user insights

## Technical Highlights

### Lambda Optimization
- Fresh Bot instances per invocation to prevent connection pool issues
- Configurable timeouts and connection limits for serverless environment
- Async/await pattern for efficient message processing

### Error Handling
- Graceful degradation when DynamoDB is unavailable
- Comprehensive logging for debugging and monitoring
- Non-blocking user data storage to maintain responsiveness

### Scalability Design
- Stateless Lambda functions for horizontal scaling
- DynamoDB's on-demand billing for variable workloads
- Infrastructure as Code for consistent deployments across environments
