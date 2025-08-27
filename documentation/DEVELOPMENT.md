# AI Assistant - Development Reference

This document serves as a quick reference guide for developers working on the AI Assistant project. It contains important commands, keys, notes, and reminders.

## 🚀 **Quick Start Commands**

### **Deploy to AWS**
```powershell
# Deploy the entire application
.\deploy.ps1

# Build SAM application locally
sam build

# Build with Docker (recommended)
sam build --use-container

# Deploy SAM application
sam deploy --guided
```

---

## 🔑 **AWS Secrets Manager Commands**

### **Telegram Bot Token**
```bash
# Create bot token secret (plain string)
aws secretsmanager create-secret \
  --name "telegram-bot-token-dev" \
  --description "Telegram Bot Token for AI Assistant" \
  --secret-string "YOUR_BOT_TOKEN_HERE"

# Update existing bot token
aws secretsmanager update-secret \
  --secret-id "telegram-bot-token-dev" \
  --secret-string "NEW_BOT_TOKEN_HERE"

# View bot token secret info
aws secretsmanager describe-secret --secret-id "telegram-bot-token-dev"

# Delete bot token secret
aws secretsmanager delete-secret \
  --secret-id "telegram-bot-token-dev" \
  --force-delete-without-recovery
```

### **Google Calendar Credentials**
```bash
# Create Google Calendar credentials (JSON format)
aws secretsmanager create-secret \
  --name "google-calendar-credentials-dev" \
  --description "Google Calendar OAuth Credentials for AI Assistant" \
  --secret-string file://creds.json

# Update Google Calendar credentials
aws secretsmanager update-secret \
  --secret-id "google-calendar-credentials-dev" \
  --secret-string file://creds.json

# View Google Calendar credentials info
aws secretsmanager describe-secret --secret-id "google-calendar-credentials-dev"

# Delete Google Calendar credentials
aws secretsmanager delete-secret \
  --secret-id "google-calendar-credentials-dev" \
  --force-delete-without-recovery
```

### **OpenAI API Key**
```bash
# Create OpenAI API key secret
aws secretsmanager create-secret \
  --name "openai-api-key-dev" \
  --description "OpenAI API Key for AI Assistant" \
  --secret-string "YOUR_OPENAI_API_KEY_HERE"

# View OpenAI API key info
aws secretsmanager describe-secret --secret-id "openai-api-key-dev"

# Delete OpenAI API key
aws secretsmanager delete-secret \
  --secret-id "openai-api-key-dev" \
  --force-delete-without-recovery
```

### **List All Secrets**
```bash
# List all development secrets
aws secretsmanager list-secrets --query "SecretList[?contains(Name, 'dev')].Name" --output table

# List all secrets
aws secretsmanager list-secrets --output table
```

---

## 🧪 **Lambda Function Testing**

### **Invoke Calendar Fetcher**
```bash
# Test calendar fetcher function
aws lambda invoke \
  --function-name aihelper-calendar-fetcher-dev \
  --payload '{}' \
  response.json

# Test with specific parameters
aws lambda invoke \
  --function-name aihelper-calendar-fetcher-dev \
  --payload '{"days_ahead": 7}' \
  response.json

# View response
cat response.json
```

### **Invoke Telegram Bot**
```bash
# Test telegram bot function (webhook simulation)
aws lambda invoke \
  --function-name aihelper-telegram-bot-dev \
  --payload '{"body": "{\"update_id\": 123, \"message\": {\"text\": \"/start\", \"from\": {\"id\": 123456}}}"}' \
  response.json
```

### **View Lambda Logs**
```bash
# View recent logs for calendar fetcher
aws logs tail /aws/lambda/aihelper-calendar-fetcher-dev --follow

# View recent logs for telegram bot
aws logs tail /aws/lambda/aihelper-telegram-bot-dev --follow

# View logs in CloudWatch console
# Go to: https://console.aws.amazon.com/cloudwatch/
# Navigate to: Logs > Log groups > /aws/lambda/aihelper-*
```

---

## 🗄️ **DynamoDB Operations**

### **View Tables**
```bash
# List all DynamoDB tables
aws dynamodb list-tables

# Describe specific table
aws dynamodb describe-table --table-name aihelper-users-dev

# Scan table contents (be careful with large tables)
aws dynamodb scan --table-name aihelper-users-dev --max-items 10
```

### **Query Data**
```bash
# Query user profile
aws dynamodb query \
  --table-name aihelper-users-dev \
  --key-condition-expression "user_id = :uid AND sort_key = :sk" \
  --expression-attribute-values '{":uid": {"N": "1681943565"}, ":sk": {"S": "profile"}}'

# Query calendar events for user
aws dynamodb query \
  --table-name aihelper-calendar-events-dev \
  --index-name UserTimeIndex \
  --key-condition-expression "user_id = :uid" \
  --expression-attribute-values '{":uid": {"N": "1"}}'
```

---

## 🌐 **API Gateway & Webhook**

### **Set Telegram Webhook**
```bash
# Get API Gateway URL from CloudFormation
aws cloudformation describe-stacks \
  --stack-name aihelper \
  --query "Stacks[0].Outputs[?OutputKey=='TelegramBotApiUrl'].OutputValue" \
  --output text

# Set webhook manually (replace with your API URL and bot token)
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-api-gateway-url.amazonaws.com/webhook"}'

# Get webhook info
curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo"
```

### **Test API Endpoints**
```bash
# Test webhook endpoint
curl -X POST "https://your-api-gateway-url.amazonaws.com/webhook" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

---

## 🔧 **Development & Debugging**

### **Local Testing**
```bash
# Test SAM application locally
sam local start-api

# Test specific function locally
sam local invoke CalendarFetcherFunction --event events/test-event.json

# Test with environment variables
sam local invoke CalendarFetcherFunction \
  --env-vars env.json \
  --event events/test-event.json
```

### **Environment Variables**
```bash
# Create env.json for local testing
{
  "CalendarFetcherFunction": {
    "CALENDAR_EVENTS_TABLE": "aihelper-calendar-events-dev",
    "GOOGLE_CREDENTIALS_SECRET": "google-calendar-credentials-dev",
    "ENVIRONMENT": "dev"
  }
}
```

### **Dependency Management**
```bash
# Install dependencies locally
pip install -r lambdas/telegram_bot/requirements.txt
pip install -r lambdas/calendar_fetcher/requirements.txt
pip install -r lambdas/shared/requirements.txt

# Update requirements
pip freeze > requirements.txt
```

---

## 📊 **Monitoring & Logs**

### **CloudWatch Metrics**
```bash
# View Lambda function metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=aihelper-calendar-fetcher-dev \
  --start-time $(date -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Average
```

### **Error Tracking**
```bash
# View recent errors in CloudWatch
aws logs filter-log-events \
  --log-group-name /aws/lambda/aihelper-calendar-fetcher-dev \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' --iso-8601)
```

---

## 🚨 **Troubleshooting**

### **Common Issues & Solutions**

#### **1. Lambda Function Errors**
- **Runtime.MarshalError**: Check if handler returns proper JSON response
- **Import errors**: Verify requirements.txt and dependencies
- **Timeout errors**: Check function timeout settings in template.yaml

#### **2. Secrets Manager Issues**
- **Invalid JSON**: Ensure Google credentials are valid JSON format
- **Access denied**: Check IAM permissions for Lambda functions
- **Secret not found**: Verify secret names match environment variables

#### **3. DynamoDB Issues**
- **Table not found**: Check table names in environment variables
- **Access denied**: Verify Lambda execution role has DynamoDB permissions
- **Schema mismatch**: Check table structure matches code expectations

#### **4. Google Calendar API Issues**
- **Invalid grant**: Refresh token expired, get new one from OAuth Playground
- **Redirect URI mismatch**: Add OAuth Playground URL to Google Cloud Console
- **Quota exceeded**: Check Google Calendar API quotas

---

## 📝 **Development Notes**

### **Important Reminders**
- ✅ **Always test locally** before deploying to AWS
- ✅ **Check CloudWatch logs** for debugging
- ✅ **Update documentation** when making schema changes
- ✅ **Use environment variables** for configuration
- ✅ **Test webhook endpoints** after deployment
- ✅ **Monitor Lambda function** performance and errors

### **Security Best Practices**
- 🔒 **Never commit secrets** to version control
- 🔒 **Use AWS Secrets Manager** for all sensitive data
- 🔒 **Rotate credentials** regularly
- 🔒 **Monitor access logs** for suspicious activity
- 🔒 **Use least privilege** IAM policies

### **Performance Tips**
- ⚡ **Use connection pooling** for external APIs
- ⚡ **Implement caching** for frequently accessed data
- ⚡ **Optimize DynamoDB queries** with proper indexes
- ⚡ **Monitor cold start** times for Lambda functions
- ⚡ **Use async operations** where possible

---

## 🔗 **Useful Links**

### **AWS Services**
- [AWS Lambda Console](https://console.aws.amazon.com/lambda/)
- [AWS DynamoDB Console](https://console.aws.amazon.com/dynamodb/)
- [AWS Secrets Manager Console](https://console.aws.amazon.com/secretsmanager/)
- [AWS CloudWatch Console](https://console.aws.amazon.com/cloudwatch/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)

### **External Services**
- [Google Cloud Console](https://console.cloud.google.com/)
- [Google OAuth Playground](https://developers.google.com/oauthplayground/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

### **Project Documentation**
- [README.md](./README.md) - Project overview
- [VERSION_HISTORY.md](./VERSION_HISTORY.md) - Development history
- [SCHEMA_DOCUMENTATION.md](./SCHEMA_DOCUMENTATION.md) - Data schemas
- [template.yaml](./template.yaml) - Infrastructure definition

---

**Last Updated**: 2025-08-27  
**Maintainer**: AI Assistant Development Team  
**Purpose**: Development reference and quick commands guide
