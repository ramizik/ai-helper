# AI Helper - Cloud-Native AI Assistant

A cloud-native AI assistant built on AWS serverless architecture, designed to provide calendar management, reminders, and productivity assistance through Telegram integration.

## 🎯 **Current Status**

**✅ PHASE 2 COMPLETE** - Telegram Bot and Calendar Integration operational  
**🚀 PHASE 3 NEXT** - AI processing with LangChain integration

## Project Overview

This project implements an AI assistant that operates in the cloud using AWS services. The system currently processes messages via webhooks, manages calendar events, and sends automated reminders. It's ready for AI-powered insights and autonomous operation.

## 🏗️ **Architecture**

### Core Components

**Multi-Lambda Architecture**
- **Telegram Bot Function** ✅ **IMPLEMENTED** - Webhook-based message processing
- **Calendar Fetcher Function** ✅ **IMPLEMENTED** - Google Calendar integration and sync
- **Scheduler Function** ✅ **IMPLEMENTED** - Automated reminders and notifications (testing: every minute)
- **AI Processor Function** 📋 **PLANNED** - LangChain-powered AI processing and memory
- **Notifier Function** 📋 **PLANNED** - Proactive message delivery to users

**AWS Infrastructure** ✅ **DEPLOYED**
- **API Gateway** - RESTful webhook endpoint for Telegram
- **DynamoDB Tables** - Users, Calendar Events (AI Memory and Notifications planned)
- **EventBridge Rules** ✅ **DEPLOYED** - Automated scheduling (Calendar sync hourly, Scheduler every minute for testing)
- **Secrets Manager** - Secure storage for API keys and credentials
- **CloudWatch** - Comprehensive logging and monitoring

## 🛠️ **Technology Stack**

### Backend Infrastructure ✅ **OPERATIONAL**
- **AWS Lambda** - Serverless compute (Python 3.13 runtime)
- **Amazon API Gateway** - HTTP API management
- **Amazon DynamoDB** - NoSQL database storage
- **Amazon EventBridge** ✅ **DEPLOYED** - Event-driven scheduling
- **AWS Secrets Manager** - Secure credential storage
- **Amazon CloudWatch** - Logging and monitoring
- **AWS CloudFormation/SAM** - Infrastructure as Code

### AI & Integration
- **LangChain** 📋 **PLANNED** - AI framework for intelligent processing
- **Google Calendar API** ✅ **INTEGRATED** - Calendar event management
- **OpenAI API** 📋 **PLANNED** - AI-powered insights and responses
- **python-telegram-bot** v20.6 ✅ **IMPLEMENTED** - Telegram Bot API wrapper

### Development & Deployment ✅ **OPERATIONAL**
- **AWS SAM CLI** - Serverless Application Model
- **Docker** - Container-based dependency management
- **PowerShell** - Automated deployment scripting
- **Git** - Version control and collaboration

## 🔄 **Component Interaction**

```
Telegram API ←→ API Gateway ←→ Lambda Functions ←→ AWS Services
                     ↓                           ↓
               EventBridge Rules            DynamoDB + Secrets
                     ↓                           ↓
               Scheduled Tasks              AI Processing
```

### **Current Working Flow**:
1. **Message Flow**: User sends message → Telegram → API Gateway webhook → Lambda function ✅
2. **Calendar Integration**: Manual sync with Google Calendar → Store events ✅
3. **Data Persistence**: All interactions stored in DynamoDB ✅
4. **Automated Reminders**: Scheduler runs every minute → Fetches current event from Google Calendar → Sends Telegram notifications ✅

### **Planned Future Flow**:
4. **AI Processing**: Lambda processes with AI context → Stores in memory → Generates intelligent response 📋
5. **Proactive Notifications**: EventBridge triggers → AI analysis → Send relevant updates to users 📋

## 📁 **File Structure**

### Core Application
- `lambdas/telegram_bot/` ✅ **IMPLEMENTED** - Telegram webhook handler
- `lambdas/calendar_fetcher/` ✅ **IMPLEMENTED** - Google Calendar integration
- `lambdas/scheduler/` ✅ **IMPLEMENTED** - Automated reminders and notifications
- `lambdas/ai_processor/` 📋 **PLANNED** - AI processing and memory management
- `lambdas/notifier/` 📋 **PLANNED** - Notification delivery system

### Infrastructure & Configuration ✅ **DEPLOYED**
- `template.yaml` - AWS SAM infrastructure definition
- `deploy.ps1` - AWS deployment automation
- `toggle-scheduler.ps1` - Scheduler on/off control
- `tail-logs.ps1` - Real-time log monitoring

### Documentation ✅ **COMPLETE**
- `PROJECT_STRUCTURE.md` - Detailed architecture documentation
- `DEVELOPMENT.md` - Development reference and commands
- `docs/` - Technical documentation and API references

## 🎉 **Current Capabilities**

### Bot Commands ✅ **FULLY FUNCTIONAL**
- **`/start`** - User registration with personalized greeting
- **`/help`** - Command assistance and bot information
- **`/test`** - Test bot functionality and database connection

### Automated Reminders ✅ **IMPLEMENTED**
- **Every Minute (Testing)**: Scheduler automatically sends users information about their current calendar event
- **Morning Summary (7 AM)**: Daily morning message with complete list of all events for the day
- **Real-Time Data**: Fetches events directly from Google Calendar API (not from database)
- **Multi-Calendar Support**: Queries all accessible calendars, not just primary
- **Smart Message Types**: Automatically switches between current event reminders and morning summaries
- **Next Event Detection**: Shows upcoming events with countdown timers
- **All-Day Event Filtering**: Skips day-long events in current event notifications

### Calendar Integration ✅ **FULLY FUNCTIONAL**
- **Google Calendar API** - Secure OAuth 2.0 authentication
- **Event Fetching** - Retrieve today's and upcoming events
- **DynamoDB Storage** - Structured event data with metadata
- **Manual Testing** - Lambda function can be invoked for testing

### Infrastructure Features ✅ **OPERATIONAL**
- **Auto-scaling** - Handles traffic spikes automatically
- **Fault tolerance** - DynamoDB backup and Lambda retry logic
- **Security** - Encrypted credential storage and IAM-based permissions
- **Cost optimization** - Pay-per-use serverless model (~$5-20/month)

## 🚀 **Deployment Status**

This is a **fully cloud-native** system with no local development files:
- ✅ **Telegram Bot** - Deployed and responding to messages
- ✅ **Calendar Fetcher** - Deployed and can fetch Google Calendar events
- ✅ **Scheduler** - Deployed and sending automated reminders
- ✅ **Infrastructure** - All AWS resources created and operational
- ✅ **Secrets Management** - Credentials securely stored in AWS Secrets Manager
- 📋 **AI Features** - Ready for LangChain integration

## 🔧 **Developer Commands & Operations**

### **Scheduler Control (Pause/Unpause)**
```powershell
# Check current status
.\toggle-scheduler.ps1 status

# Pause scheduler (stop sending messages)
.\toggle-scheduler.ps1 off

# Resume scheduler (start sending messages again)
.\toggle-scheduler.ps1 on
```

### **Real-Time Log Monitoring**
```powershell
# Monitor all Lambda functions in real-time
.\tail-logs.ps1

# Monitor specific function (replace FUNCTION_NAME)
aws logs tail "/aws/lambda/FUNCTION_NAME" --follow --region us-west-2

# Example: Monitor scheduler
aws logs tail "/aws/lambda/aihelper-scheduler-dev" --follow --region us-west-2
```

### **Cost Monitoring**
```powershell
# Get today's total AWS cost
$today = Get-Date -Format "yyyy-MM-dd"
$tomorrow = (Get-Date).AddDays(1).ToString("yyyy-MM-dd")
aws ce get-cost-and-usage --time-period Start=$today,End=$tomorrow --granularity=DAILY --metrics=UnblendedCost --query "ResultsByTime[0].Total.UnblendedCost.Amount" --output text

# Get cost breakdown by service
aws ce get-cost-and-usage --time-period Start=$today,End=$tomorrow --granularity=DAILY --metrics=UnblendedCost --group-by Type=DIMENSION,Key=SERVICE --query "ResultsByTime[0].Groups[].{Service:Keys[0],Cost:Metrics.UnblendedCost.Amount}" --output table
```

### **Testing Functions**
```powershell
# Test Calendar Fetcher
aws lambda invoke --function-name aihelper-calendar-fetcher-dev --payload '{}' response.json

# Test Scheduler manually
aws lambda invoke --function-name aihelper-scheduler-dev --payload '{}' response.json

# Check function status
aws lambda get-function --function-name aihelper-scheduler-dev --region us-west-2 --query "Configuration.State" --output text
```

## 📋 **Next Development Phase**

### **Phase 3: AI Core Integration** 🚀
- [ ] **LangChain Setup** - Install and configure LangChain dependencies
- [ ] **AI Processor** - Implement intelligent event analysis
- [ ] **Memory Management** - Store and retrieve AI context
- [ ] **Smart Summaries** - Generate daily schedule insights
- [ ] **Intelligent Reminders** - AI-powered notification timing

### **Future Phases**:
- **Phase 4**: Proactive notifications and smart reminders
- **Phase 5**: Advanced AI features and learning capabilities
- **Phase 6**: Multi-platform integration (Notion, Slack, etc.)

## 📚 **Documentation**

- **[VERSION_HISTORY.md](./documentation/VERSION_HISTORY.md)** - Complete development timeline
- **[SCHEMA_DOCUMENTATION.md](./documentation/SCHEMA_DOCUMENTATION.md)** - Data models and schemas
- **[DEVELOPMENT.md](./documentation/DEVELOPMENT.md)** - Commands and development reference
- **[PROJECT_STRUCTURE.md](./documentation/PROJECT_STRUCTURE.md)** - Detailed architecture overview

## 🎯 **Getting Started**

### **For Users**:
1. **Start a conversation** with your bot on Telegram
2. **Use commands** like `/start`, `/help`, `/test`
3. **Receive automated reminders** about current and upcoming events

### **For Developers**:
1. **Review current implementation** in `lambdas/` folders
2. **Check deployment status** in AWS Console
3. **Use provided scripts** for scheduler control and log monitoring
4. **Test functions** using AWS CLI commands
5. **Plan next phase** with LangChain integration

---

**Current Status**: ✅ **Telegram Bot + Calendar Integration + Automated Reminders = OPERATIONAL**  
**Next Goal**: 🚀 **AI Processing with LangChain**  
**Deployment**: 🌐 **100% Cloud-Native on AWS**  
**Cost**: 💰 **Serverless - Pay per use (~$5-20/month)**
