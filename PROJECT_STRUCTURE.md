# AI Assistant Project Structure

## 📁 **Project Organization**

```
ai-helper/
├── 📁 lambdas/                    # Lambda function code
│   ├── 📁 telegram_bot/          # Telegram Bot (reactive)
│   │   ├── handler.py            # Main bot logic
│   │   └── requirements.txt      # Python dependencies
│   ├── 📁 calendar_fetcher/      # Google Calendar integration
│   │   ├── handler.py            # Calendar sync logic
│   │   └── requirements.txt      # Google API dependencies
│   ├── 📁 ai_processor/          # LLM processing & AI brain
│   │   ├── handler.py            # AI processing logic
│   │   └── requirements.txt      # LangChain dependencies
│   ├── 📁 scheduler/             # Workflow orchestration
│   │   ├── handler.py            # Scheduling logic
│   │   └── requirements.txt      # Basic dependencies
│   ├── 📁 notifier/              # Proactive messaging
│   │   ├── handler.py            # Message composition
│   │   └── requirements.txt      # Telegram dependencies
│   └── 📁 shared/                # Common utilities
│       ├── db_models.py          # DynamoDB schemas
│       ├── auth_manager.py       # API authentication
│       └── requirements.txt      # Shared dependencies
├── 📁 infrastructure/             # AWS infrastructure
│   ├── template.yaml             # SAM template
│   ├── 📁 parameters/            # Environment configs
│   └── 📁 scripts/               # Deployment scripts
│       └── deploy.ps1            # Enhanced deployment
├── 📁 docs/                      # Documentation
├── 📁 config/                    # Configuration files
├── 📁 tests/                     # Unit tests
├── architecture_plan.md          # Detailed architecture
├── PROJECT_STRUCTURE.md          # This file
└── README.md                     # Project overview
```

## 🔄 **Lambda Functions Overview**

### **1. Telegram Bot Lambda** (`lambdas/telegram_bot/`)
- **Purpose**: Handle user interactions via Telegram
- **Trigger**: API Gateway webhook
- **Responsibilities**: 
  - Process user commands (`/start`, `/help`, etc.)
  - Provide manual updates and information
  - Handle conversation flow
  - Store user interactions in DynamoDB

### **2. Calendar Fetcher Lambda** (`lambdas/calendar_fetcher/`)
- **Purpose**: Sync Google Calendar events
- **Trigger**: EventBridge (every hour) + manual
- **Responsibilities**:
  - Authenticate with Google Calendar API
  - Fetch today's and upcoming events
  - Store events in DynamoDB
  - Handle all-day vs timed events
  - Extract event metadata (attendees, location, etc.)

### **3. AI Processor Lambda** (`lambdas/ai_processor/`)
- **Purpose**: LLM processing and decision making
- **Trigger**: EventBridge (8 AM daily) + SQS messages
- **Responsibilities**:
  - Generate morning summaries
  - Analyze calendar events
  - Create contextual insights
  - Manage AI memory and context
  - Decide on notifications

### **4. Scheduler Lambda** (`lambdas/scheduler/`)
- **Purpose**: Orchestrate AI workflows
- **Trigger**: EventBridge (every 30 minutes)
- **Responsibilities**:
  - Check current time vs user's calendar
  - Determine what actions to take
  - Queue AI processing tasks
  - Trigger proactive notifications

### **5. Notifier Lambda** (`lambdas/notifier/`)
- **Purpose**: Send proactive Telegram messages
- **Trigger**: SQS messages from AI Processor
- **Responsibilities**:
  - Compose contextual messages
  - Send via Telegram Bot API
  - Log notification history
  - Handle delivery status

## 🗄️ **Database Schema**

### **DynamoDB Tables**

#### **Users Table** (`aihelper-users-{env}`)
- **Partition Key**: `user_id` (Telegram user ID)
- **Range Key**: `sort_key` (e.g., "profile", "settings")
- **Stores**: User profiles, preferences, timezone

#### **Calendar Events Table** (`aihelper-calendar-events-{env}`)
- **Partition Key**: `user_id`
- **Range Key**: `sort_key` (e.g., "event_{timestamp}_{event_id}")
- **Stores**: Google Calendar events, sync status, AI processing flags

#### **AI Memory Table** (`aihelper-ai-memory-{env}`)
- **Partition Key**: `user_id`
- **Range Key**: `sort_key` (e.g., "memory_{date}_{type}")
- **Stores**: AI context, daily summaries, insights (with TTL)

#### **Notifications Table** (`aihelper-notifications-{env}`)
- **Partition Key**: `user_id`
- **Range Key**: `sort_key` (e.g., "notification_{timestamp}_{type}")
- **Stores**: Message history, delivery status, related events

## 🔐 **Authentication & Secrets**

### **AWS Secrets Manager**
- **`google-calendar-credentials-{env}`**: Google OAuth2 credentials
- **`openai-api-key-{env}`**: OpenAI API key
- **`telegram-bot-token-{env}`**: Telegram Bot token

### **Environment Variables**
- **`USER_ID`**: Your Telegram user ID (hardcoded for single-user system)
- **`CALENDAR_EVENTS_TABLE`**: DynamoDB table name
- **`AI_MEMORY_TABLE`**: AI memory table name
- **`NOTIFICATIONS_TABLE`**: Notifications table name

## 📅 **Scheduling & Automation**

### **EventBridge Rules**
- **Morning Summary**: 8 AM daily → AI Processor
- **Regular Check**: Every 30 minutes → Scheduler
- **Calendar Sync**: Every hour → Calendar Fetcher

## 🚀 **Deployment Process**

### **1. Prerequisites**
- AWS CLI configured
- SAM CLI installed
- Python 3.13+
- PowerShell 5.1+

### **2. Setup Secrets**
```bash
# Google Calendar API credentials
aws secretsmanager create-secret \
  --name "google-calendar-credentials-dev" \
  --secret-string '{"client_id":"...","client_secret":"...","refresh_token":"..."}'

# OpenAI API key
aws secretsmanager create-secret \
  --name "openai-api-key-dev" \
  --secret-string '{"api_key":"sk-..."}'
```

### **3. Deploy Stack**
```powershell
# Navigate to infrastructure/scripts
cd infrastructure/scripts

# Deploy to dev environment
.\deploy.ps1 -Environment dev

# Deploy to prod environment
.\deploy.ps1 -Environment prod
```

## 🔧 **Development Workflow**

### **Local Development**
1. **Set up environment**: Create `.env` file with your credentials
2. **Test individual functions**: Use SAM local invoke
3. **Test full stack**: Use SAM local start-api

### **Testing**
```bash
# Test Calendar Fetcher locally
sam local invoke CalendarFetcherFunction --env-vars env.json

# Test Telegram Bot locally
sam local start-api
```

### **Debugging**
- **CloudWatch Logs**: Each Lambda has its own log group
- **X-Ray Tracing**: Available for request tracing
- **Local Testing**: Use SAM local for faster iteration

## 📚 **Key Files to Understand**

### **Start Here** (if new to the project):
1. `architecture_plan.md` - Complete system overview
2. `lambdas/telegram_bot/handler.py` - Basic bot functionality
3. `infrastructure/template.yaml` - Infrastructure definition

### **For Calendar Integration**:
1. `lambdas/calendar_fetcher/handler.py` - Calendar sync logic
2. `lambdas/shared/auth_manager.py` - Google API authentication
3. `lambdas/shared/db_models.py` - Database schemas

### **For AI Features**:
1. `lambdas/ai_processor/handler.py` - AI processing logic
2. `lambdas/scheduler/handler.py` - Workflow orchestration
3. `lambdas/notifier/handler.py` - Proactive messaging

## 🎯 **Next Steps**

### **Phase 1: Foundation** ✅
- [x] Project structure created
- [x] Basic Lambda functions defined
- [x] DynamoDB schemas designed
- [x] SAM template created

### **Phase 2: Calendar Integration** 🚧
- [ ] Set up Google Calendar API credentials
- [ ] Test Calendar Fetcher Lambda
- [ ] Verify DynamoDB event storage
- [ ] Test EventBridge scheduling

### **Phase 3: AI Core** 📋
- [ ] Implement AI Processor with LangChain
- [ ] Add memory management
- [ ] Create morning summary functionality
- [ ] Test AI workflows

### **Phase 4: Proactive Features** 📋
- [ ] Implement Scheduler and Notifier
- [ ] Test proactive messaging
- [ ] Optimize scheduling logic
- [ ] Add user preferences

## 💡 **Tips for Development**

1. **Start Small**: Test Calendar Fetcher first, then add AI features
2. **Use CloudWatch**: Monitor Lambda executions and errors
3. **Test Locally**: Use SAM local for faster development cycles
4. **Check Permissions**: Ensure IAM roles have correct permissions
5. **Monitor Costs**: DynamoDB and Lambda costs can add up quickly

## 🆘 **Troubleshooting**

### **Common Issues**:
- **Import Errors**: Check Python path and Lambda layers
- **Permission Denied**: Verify IAM roles and policies
- **Timeout Errors**: Increase Lambda timeout or optimize code
- **Cold Starts**: Use provisioned concurrency for critical functions

### **Getting Help**:
- Check CloudWatch logs for detailed error messages
- Use AWS X-Ray for request tracing
- Test individual components locally first
- Verify environment variables and secrets

---

**Happy coding! 🚀** This structure provides a solid foundation for building your AI personal assistant.
