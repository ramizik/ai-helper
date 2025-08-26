# Deploy Basic Telegram Bot to AWS

This guide will help you deploy your basic Telegram bot to AWS for testing before adding AI features.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **AWS SAM CLI** installed
4. **Telegram Bot Token** (from @BotFather)

## Installation Steps

### Step 1: Install AWS SAM CLI

```powershell
# On Windows (using Chocolatey)
choco install aws-sam-cli

# Or download from: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install-windows.html
```

### Step 2: Configure AWS CLI

```powershell
aws configure
```

Enter your AWS credentials when prompted.

### Step 3: Prepare Your Bot Token

Make sure you have your Telegram bot token ready. If you don't have one:
1. Message @BotFather on Telegram
2. Use `/newbot` command
3. Follow instructions to get your token

### Step 4: Deploy to AWS

```powershell
# Build the SAM application
sam build

# Deploy (first time)
sam deploy --guided --parameter-overrides BotToken=YOUR_BOT_TOKEN_HERE
```

**During guided deployment:**
- Stack Name: `aihelper-dev`
- AWS Region: Choose your preferred region (e.g., `us-east-1`)
- Parameter BotToken: Paste your telegram bot token
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Save parameters to config file: `Y`

### Step 5: Set Up Telegram Webhook

After deployment completes, you'll see a webhook URL in the outputs. Use it to register your webhook:

```powershell
# Replace with your actual webhook URL and bot token
$webhookUrl = "https://your-api-id.execute-api.us-east-1.amazonaws.com/dev/webhook"
$botToken = "YOUR_BOT_TOKEN"

curl -X POST "https://api.telegram.org/bot$botToken/setWebhook" -d "url=$webhookUrl"
```

## Verify Deployment

1. **Test Bot**: Send `/start` to your bot on Telegram
2. **Check Logs**: View CloudWatch logs in AWS console
3. **Monitor Schedules**: EventBridge rules should be active

## Cost Monitoring

Your monthly costs should be approximately:
- **Lambda**: $0-5 (1M free requests/month)
- **API Gateway**: $1-3 (1M free requests/month)
- **DynamoDB**: $1-5 (25GB free storage)

**Total: ~$2-13/month** for moderate usage (mostly free tier!)

## Configuration Options

### Modify Schedules

Edit the cron expressions in `template.yaml`:

```yaml
# Morning summary at 8 AM daily
ScheduleExpression: 'cron(0 8 * * ? *)'

# Periodic reminders every 30 minutes, 9AM-5PM weekdays
ScheduleExpression: 'cron(0/30 9-17 ? * MON-FRI *)'

# Evening recap at 8 PM daily
ScheduleExpression: 'cron(0 20 * * ? *)'
```

### Update After Changes

```powershell
sam build
sam deploy
```

## Troubleshooting

### Common Issues

1. **Bot Not Responding**
   - Check webhook is set correctly
   - Verify bot token in Parameter Store
   - Check CloudWatch logs

2. **Scheduled Messages Not Sending**
   - Verify EventBridge rules are enabled
   - Check scheduler function logs
   - Ensure users exist in DynamoDB table

3. **Deployment Fails**
   - Verify AWS credentials
   - Check IAM permissions
   - Ensure unique stack name

### Useful Commands

```powershell
# View stack outputs
aws cloudformation describe-stacks --stack-name aihelper-dev --query 'Stacks[0].Outputs'

# Check DynamoDB table
aws dynamodb scan --table-name aihelper-users-dev

# View recent logs
sam logs -n TelegramBotFunction --tail

# Delete stack (cleanup)
sam delete --stack-name aihelper-dev
```

## Security Notes

- Bot token is stored encrypted in Parameter Store
- DynamoDB has point-in-time recovery enabled
- IAM roles follow least-privilege principle
- CloudTrail tracks all API calls

## Next Steps

Once deployed successfully, you can:
1. **Add AI Integration** - Connect to OpenAI/Claude APIs
2. **Calendar Integration** - Connect Google Calendar or Outlook
3. **User Preferences** - Add timezone and notification settings
4. **Analytics** - Track user engagement and bot performance
5. **Advanced Features** - File uploads, voice messages, etc.

## Support

If you encounter issues:
1. Check CloudWatch logs first
2. Verify all prerequisites are met
3. Ensure correct AWS permissions
4. Test with a simple message to isolate issues
