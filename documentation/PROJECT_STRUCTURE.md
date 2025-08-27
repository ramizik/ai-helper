# AI Assistant Project Structure

## 📁 **Project Organization**

```
ai-helper/
├── 📁 lambdas/                    # Lambda function code
│   ├── 📁 telegram_bot/          # Telegram Bot (reactive) ✅ IMPLEMENTED
│   │   ├── handler.py            # Main bot logic
│   │   └── requirements.txt      # Python dependencies
│   ├── 📁 calendar_fetcher/      # Google Calendar integration ✅ IMPLEMENTED
│   │   ├── handler.py            # Calendar sync logic
│   │   └── requirements.txt      # Google API dependencies
│   ├── 📁 ai_processor/          # LLM processing & AI brain 📋 PLANNED
│   │   ├── handler.py            # AI processing logic
│   │   └── requirements.txt      # LangChain dependencies
│   ├── 📁 scheduler/             # Workflow orchestration 📋 PLANNED
│   │   ├── handler.py            # Scheduling logic
│   │   └── requirements.txt      # Basic dependencies
│   ├── 📁 notifier/              # Proactive messaging 📋 PLANNED
│   │   ├── handler.py            # Message composition
│   │   └── requirements.txt      # Telegram dependencies
│   └── 📁 shared/                # Common utilities ✅ IMPLEMENTED
│       ├── db_models.py          # DynamoDB schemas
│       ├── auth_manager.py       # API authentication
│       └── requirements.txt      # Shared dependencies
├── 📁 infrastructure/             # AWS infrastructure
│   ├── template.yaml             # SAM template ✅ IMPLEMENTED
│   ├── 📁 parameters/            # Environment configs
│   └── 📁 scripts/               # Deployment scripts
│       └── deploy.ps1            # Enhanced deployment ✅ IMPLEMENTED
├── 📁 docs/                      # Documentation
├── 📁 config/                    # Configuration files
├── 📁 tests/                     # Unit tests
├── architecture_plan.md          # Detailed architecture
├── PROJECT_STRUCTURE.md          # This file
└── README.md                     # Project overview
```

## 🔄 **Lambda Functions Overview**

### **1. Telegram Bot Lambda** (`lambdas/telegram_bot/`) ✅ **IMPLEMENTED**
- **Purpose**: Handle user interactions via Telegram
- **Trigger**: API Gateway webhook
- **Status**: ✅ **Fully deployed and functional**
- **Responsibilities**: 
  - Process user commands (`/start`, `/help`, `/test`)
  - Provide manual updates and information
  - Handle conversation flow
  - Store user interactions in DynamoDB

### **2. Calendar Fetcher Lambda** (`lambdas/calendar_fetcher/`) ✅ **IMPLEMENTED**
- **Purpose**: Sync Google Calendar events
- **Trigger**: Manual invocation + EventBridge (planned)
- **Status**: ✅ **Fully deployed and functional**
- **Responsibilities**:
  - Authenticate with Google Calendar API
  - Fetch today's and upcoming events
  - Store events in DynamoDB
  - Handle all-day vs timed events
  - Extract event metadata (attendees, location, etc.)

### **3. AI Processor Lambda** (`lambdas/ai_processor/`) 📋 **PLANNED**
- **Purpose**: LLM processing and decision making
- **Trigger**: EventBridge (8 AM daily) + SQS messages
- **Status**: 📋 **Architecture designed, not implemented**
- **Responsibilities**:
  - Generate morning summaries
  - Analyze calendar events
  - Create contextual insights
  - Manage AI memory and context
  - Decide on notifications

### **4. Scheduler Lambda** (`lambdas/scheduler/`) 📋 **PLANNED**
- **Purpose**: Orchestrate AI workflows
- **Trigger**: EventBridge (every 30 minutes)
- **Status**: 📋 **Architecture designed, not implemented**
- **Responsibilities**:
  - Check current time vs user's calendar
  - Determine what actions to take
  - Queue AI processing tasks
  - Trigger proactive notifications

### **5. Notifier Lambda** (`lambdas/notifier/`) 📋 **PLANNED**
- **Purpose**: Send proactive Telegram messages
- **Trigger**: SQS messages from AI Processor
- **Status**: 📋 **Architecture designed, not implemented**
- **Responsibilities**:
  - Compose contextual messages
  - Send via Telegram Bot API
  - Log notification history
  - Handle delivery status

## 🗄️ **Database Schema**

### **DynamoDB Tables**

#### **Users Table** (`aihelper-users-{env}`) ✅ **IMPLEMENTED**
- **Partition Key**: `user_id` (Telegram user ID)
- **Range Key**: `sort_key` (e.g., "profile", "settings")
- **Stores**: User profiles, preferences, timezone
- **Status**: ✅ **Created and operational**

#### **Calendar Events Table** (`aihelper-calendar-events-{env}`) ✅ **IMPLEMENTED**
- **Partition Key**: `event_id`
- **Range Key**: `start_time`
- **Global Secondary Index**: `UserTimeIndex` for user-based queries
- **Stores**: Google Calendar events, sync status, AI processing flags
- **Status**: ✅ **Created and operational**

#### **AI Memory Table** (`aihelper-ai-memory-{env}`) 📋 **PLANNED**
- **Partition Key**: `user_id`
- **Range Key**: `sort_key` (e.g., "memory_{date}_{type}")
- **Stores**: AI context, daily summaries, insights (with TTL)
- **Status**: 📋 **Schema designed, not created**

#### **Notifications Table** (`aihelper-notifications-{env}`) 📋 **PLANNED**
- **Partition Key**: `user_id`
- **Range Key**: `sort_key` (e.g., "notification_{timestamp}_{type}")
- **Stores**: Message history, delivery status, related events
- **Status**: 📋 **Schema designed, not created**

## 🔐 **Authentication & Secrets**

### **AWS Secrets Manager** ✅ **IMPLEMENTED**
- **`google-calendar-credentials-{env}`**: Google OAuth2 credentials ✅ **Created**
- **`telegram-bot-token-{env}`**: Telegram Bot token ✅ **Created**
- **`openai-api-key-{env}`**: OpenAI API key 📋 **Planned for future AI features**

### **Environment Variables** ✅ **CONFIGURED**
- **`CALENDAR_EVENTS_TABLE`**: DynamoDB table name ✅ **Set**
- **`GOOGLE_CREDENTIALS_SECRET`**: Google credentials secret name ✅ **Set**
- **`BOT_TOKEN_SECRET`**: Telegram bot token secret name ✅ **Set**

## 📅 **Scheduling & Automation**

### **EventBridge Rules** 📋 **PLANNED**
- **Morning Summary**: 8 AM daily → AI Processor (not implemented)
- **Regular Check**: Every 30 minutes → Scheduler (not implemented)
- **Calendar Sync**: Every hour → Calendar Fetcher (not implemented)

### **Current Status**: Manual invocation only

## 🚀 **Deployment Process**

### **1. Prerequisites** ✅ **COMPLETED**
- AWS CLI configured ✅
- SAM CLI installed ✅
- Python 3.13+ ✅
- PowerShell 5.1+ ✅

### **2. Setup Secrets** ✅ **COMPLETED**
```bash
# Google Calendar API credentials ✅ CREATED
aws secretsmanager create-secret \
  --name "google-calendar-credentials-dev" \
  --secret-string '{"client_id":"...","client_secret":"...","refresh_token":"..."}'

# Telegram Bot token ✅ CREATED
aws secretsmanager create-secret \
  --name "telegram-bot-token-dev" \
  --secret-string "YOUR_BOT_TOKEN"
```

### **3. Deploy Stack** ✅ **COMPLETED**
```powershell
# Deploy to dev environment ✅ DONE
.\deploy.ps1
```

## 🔧 **Development Workflow**

### **Current Status** ✅ **OPERATIONAL**
- **Telegram Bot**: Fully functional via webhook
- **Calendar Fetcher**: Can be manually invoked for testing
- **Infrastructure**: All AWS resources created and operational

### **Local Development** 📋 **PLANNED**
1. **Set up environment**: Create `.env` file with your credentials
2. **Test individual functions**: Use SAM local invoke
3. **Test full stack**: Use SAM local start-api

### **Testing** ✅ **AVAILABLE**
```bash
# Test Calendar Fetcher (deployed)
aws lambda invoke --function-name aihelper-calendar-fetcher-dev --payload '{}' response.json

# Test Telegram Bot (deployed)
# Send messages to your bot on Telegram
```

### **Debugging** ✅ **AVAILABLE**
- **CloudWatch Logs**: Each Lambda has its own log group ✅
- **X-Ray Tracing**: Available for request tracing ✅
- **Local Testing**: Use SAM local for faster iteration 📋

## 📚 **Key Files to Understand**

### **Start Here** (if new to the project):
1. `README.md` - Project overview and current status
2. `lambdas/telegram_bot/handler.py` - Basic bot functionality ✅
3. `template.yaml` - Infrastructure definition ✅

### **For Calendar Integration**:
1. `lambdas/calendar_fetcher/handler.py` - Calendar sync logic ✅
2. `lambdas/shared/auth_manager.py` - Google API authentication ✅
3. `lambdas/shared/db_models.py` - Database schemas ✅

### **For Future AI Features**:
1. `lambdas/ai_processor/handler.py` - AI processing logic 📋
2. `lambdas/scheduler/handler.py` - Workflow orchestration 📋
3. `lambdas/notifier/handler.py` - Proactive messaging 📋

## 🎯 **Current Status & Next Steps**

### **Phase 1: Foundation** ✅ **COMPLETED**
- [x] Project structure created
- [x] Basic Lambda functions defined
- [x] DynamoDB schemas designed
- [x] SAM template created
- [x] Telegram Bot deployed and functional
- [x] Calendar Fetcher deployed and functional

### **Phase 2: Calendar Integration** ✅ **COMPLETED**
- [x] Set up Google Calendar API credentials
- [x] Deploy Calendar Fetcher Lambda
- [x] Verify DynamoDB event storage
- [x] Test manual invocation

### **Phase 3: AI Core** 📋 **NEXT PRIORITY**
- [ ] Implement AI Processor with LangChain
- [ ] Add memory management
- [ ] Create morning summary functionality
- [ ] Test AI workflows

### **Phase 4: Proactive Features** 📋 **FUTURE**
- [ ] Implement Scheduler and Notifier
- [ ] Test proactive messaging
- [ ] Optimize scheduling logic
- [ ] Add user preferences

## 💡 **Tips for Development**

1. **Current Status**: Telegram Bot and Calendar Fetcher are fully operational
2. **Next Focus**: Implement AI Processor with LangChain integration
3. **Use CloudWatch**: Monitor Lambda executions and errors
4. **Test Calendar Fetcher**: Use manual invocation to verify Google Calendar integration
5. **Check Permissions**: Ensure IAM roles have correct permissions

## 🆘 **Troubleshooting**

### **Current Working Components**:
- **Telegram Bot**: Fully functional, responds to commands
- **Calendar Fetcher**: Can fetch events from Google Calendar
- **DynamoDB**: Tables operational, data being stored

### **Common Issues**:
- **Import Errors**: Check Python path and Lambda layers
- **Permission Denied**: Verify IAM roles and policies
- **Timeout Errors**: Check Lambda timeout settings
- **Cold Starts**: Use provisioned concurrency for critical functions

### **Getting Help**:
- Check CloudWatch logs for detailed error messages
- Use AWS X-Ray for request tracing
- Test individual components using AWS CLI
- Verify environment variables and secrets

---

**Current Status**: ✅ **Phase 2 Complete** - Telegram Bot and Calendar Integration fully operational  
**Next Goal**: 🚀 **Phase 3** - Implement AI processing with LangChain  
**Happy coding! 🚀**
