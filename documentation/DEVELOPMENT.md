# AI Helper - Development Reference

This document provides essential commands and development workflows for the AI Helper project.

## 🚀 **Quick Start Commands**

### **Deploy the Project**
```powershell
# Full build and deploy
.\deploy.ps1

# Build only
sam build --use-container --config-env default

# Deploy only
sam deploy --config-env default --no-confirm-changeset --no-fail-on-empty-changeset
```

## 🔌 **Scheduler Control (Pause/Unpause)**

### **Using the Toggle Script (Recommended)**
```powershell
# Check current status
.\toggle-scheduler.ps1 status

# Pause scheduler (stop sending messages)
.\toggle-scheduler.ps1 off

# Resume scheduler (start sending messages again)
.\toggle-scheduler.ps1 on
```

### **Direct AWS CLI Commands**
```powershell
# Check scheduler status
aws events describe-rule --name "aihelper-scheduler-dev" --region us-west-2 --query "State" --output text

# Disable scheduler
aws events disable-rule --name "aihelper-scheduler-dev" --region us-west-2

# Enable scheduler
aws events enable-rule --name "aihelper-scheduler-dev" --region us-west-2
```

## 📊 **Real-Time Log Monitoring**

### **Using the Monitoring Script**
```powershell
# Monitor all Lambda functions
.\tail-logs.ps1
```

### **Direct AWS CLI Commands**
```powershell
# Monitor scheduler logs (real-time)
aws logs tail "/aws/lambda/aihelper-scheduler-dev" --follow --region us-west-2

# Monitor Telegram bot logs
aws logs tail "/aws/lambda/aihelper-telegram-bot-dev" --follow --region us-west-2

# Monitor calendar fetcher logs
aws logs tail "/aws/lambda/aihelper-calendar-fetcher-dev" --follow --region us-west-2

# Get recent logs (last 10 events)
aws logs get-log-events --log-group-name "/aws/lambda/aihelper-scheduler-dev" --log-stream-name "latest" --limit 10 --region us-west-2
```

## 💰 **Cost Monitoring**

### **Daily Cost Check**
```powershell
# Get today's total AWS cost
$today = Get-Date -Format "yyyy-MM-dd"
$tomorrow = (Get-Date).AddDays(1).ToString("yyyy-MM-dd")
aws ce get-cost-and-usage --time-period Start=$today,End=$tomorrow --granularity=DAILY --metrics=UnblendedCost --query "ResultsByTime[0].Total.UnblendedCost.Amount" --output text
```

### **Cost Breakdown by Service**
```powershell
# Get cost breakdown by AWS service
aws ce get-cost-and-usage --time-period Start=$today,End=$tomorrow --granularity=DAILY --metrics=UnblendedCost --group-by Type=DIMENSION,Key=SERVICE --query "ResultsByTime[0].Groups[].{Service:Keys[0],Cost:Metrics.UnblendedCost.Amount}" --output table
```

### **Monthly Cost Summary**
```powershell
# Get current month cost
$monthStart = (Get-Date).ToString("yyyy-MM-01")
$nextMonth = (Get-Date).AddMonths(1).ToString("yyyy-MM-01")
aws ce get-cost-and-usage --time-period Start=$monthStart,End=$nextMonth --granularity=MONTHLY --metrics=UnblendedCost --query "ResultsByTime[0].Total.UnblendedCost.Amount" --output text
```

## 🧪 **Testing Functions**

### **Manual Function Invocation**
```powershell
# Test Calendar Fetcher
aws lambda invoke --function-name aihelper-calendar-fetcher-dev --payload '{}' response.json

# Test Scheduler manually
aws lambda invoke --function-name aihelper-scheduler-dev --payload '{}' response.json

# Test Telegram Bot (requires webhook payload)
aws lambda invoke --function-name aihelper-telegram-bot-dev --payload '{"body": "test"}' response.json
```

### **Check Function Status**
```powershell
# Check if functions are active
aws lambda get-function --function-name aihelper-scheduler-dev --region us-west-2 --query "Configuration.State" --output text
aws lambda get-function --function-name aihelper-telegram-bot-dev --region us-west-2 --query "Configuration.State" --output text
aws lambda get-function --function-name aihelper-calendar-fetcher-dev --region us-west-2 --query "Configuration.State" --output text
```

## 🔍 **Database Operations**

### **DynamoDB Queries**
```powershell
# Check user profiles
aws dynamodb scan --table-name aihelper-users-dev --select COUNT --region us-west-2

# Check calendar events
aws dynamodb scan --table-name aihelper-calendar-events-dev --select COUNT --region us-west-2

# Get specific user profile
aws dynamodb get-item --table-name aihelper-users-dev --key '{"user_id": {"N": "1681943565"}, "sort_key": {"S": "profile"}}' --region us-west-2
```

## 🚨 **Troubleshooting**

### **Common Issues and Solutions**

#### **Scheduler Not Running**
```powershell
# Check EventBridge rule status
aws events describe-rule --name "aihelper-scheduler-dev" --region us-west-2 --query "State" --output text

# Check Lambda function status
aws lambda get-function --function-name aihelper-scheduler-dev --region us-west-2 --query "Configuration.State" --output text

# Check recent logs for errors
aws logs get-log-events --log-group-name "/aws/lambda/aihelper-scheduler-dev" --log-stream-name "latest" --limit 5 --region us-west-2
```

#### **Telegram Bot Not Responding**
```powershell
# Check webhook URL in Telegram
# Check API Gateway logs
# Check Lambda function logs
aws logs tail "/aws/lambda/aihelper-telegram-bot-dev" --follow --region us-west-2
```

#### **Calendar Events Not Fetching**
```powershell
# Check Google Calendar credentials
# Test calendar fetcher manually
aws lambda invoke --function-name aihelper-calendar-fetcher-dev --payload '{}' response.json

# Check logs for authentication errors
aws logs tail "/aws/lambda/aihelper-calendar-fetcher-dev" --follow --region us-west-2
```

## 📋 **Development Workflow**

### **1. Make Code Changes**
- Edit files in `lambdas/` directory
- Test locally if possible
- Commit changes to git

### **2. Deploy Changes**
```powershell
.\deploy.ps1
```

### **3. Monitor Deployment**
```powershell
# Check function status
aws lambda get-function --function-name aihelper-scheduler-dev --region us-west-2 --query "Configuration.State" --output text

# Monitor logs for new deployment
aws logs tail "/aws/lambda/aihelper-scheduler-dev" --follow --region us-west-2
```

### **4. Test Functionality**
- Use provided test commands
- Check CloudWatch logs
- Verify expected behavior

### **5. Pause Scheduler During Development**
```powershell
# Stop automated messages
.\toggle-scheduler.ps1 off

# Resume when ready
.\toggle-scheduler.ps1 on
```

## 🔧 **Environment Variables**

### **Lambda Environment Variables**
- `USERS_TABLE`: DynamoDB table for user profiles
- `CALENDAR_EVENTS_TABLE`: DynamoDB table for calendar events
- `BOT_TOKEN_SECRET`: Telegram bot token secret name
- `GOOGLE_CALENDAR_CREDENTIALS_SECRET`: Google Calendar credentials secret name

### **Local Development**
- Create `.env` file for local testing
- Use AWS CLI profiles for different environments
- Test with AWS SAM local if needed

## 📚 **Useful Resources**

- **AWS SAM Documentation**: https://docs.aws.amazon.com/serverless-application-model/
- **AWS Lambda Python Runtime**: https://docs.aws.amazon.com/lambda/latest/dg/python-programming-model.html
- **DynamoDB Best Practices**: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html
- **EventBridge Rules**: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rules.html

---

**Remember**: Always check logs after deployment, use the toggle script to control the scheduler, and monitor costs regularly during development.
