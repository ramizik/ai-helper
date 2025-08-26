# AI Helper - Basic Telegram Bot

A basic Telegram bot that will be incrementally enhanced with AI capabilities.

## Current Features
- `/start` - Greets the user
- `/help` - Shows help message  
- **Echo** - Repeats back any text message

## Getting Started

### 1. Local Testing (Optional)
Test the bot locally before deploying to AWS:
```powershell
python test_bot_local.py
```

### 2. Deploy to AWS
Deploy the bot to run 24/7 in the cloud:
```powershell
.\deploy.ps1 -BotToken "YOUR_BOT_TOKEN_HERE"
```

### 3. Test on Telegram
- Send `/start` → Should get "Hi {your_name}!"
- Send `/help` → Should get "Help!"  
- Send any text → Should echo it back

## Files
- `telegram_bot.py` - Original local version
- `lambda_bot.py` - AWS Lambda webhook version
- `template.yaml` - AWS infrastructure
- `test_bot_local.py` - Local testing script
- `deploy.ps1` - One-click deployment

## Next Steps
Once basic functionality is working, we'll add:
- AI-powered responses
- Scheduled reminders
- Calendar integration
- Goal tracking
