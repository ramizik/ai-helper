"""
AWS Lambda-based Telegram Bot Handler
Webhook version for cloud deployment

This function handles incoming Telegram messages via API Gateway webhook
and can be extended with AI capabilities and scheduled reminders.
"""

import json
import logging
import os
import boto3
from typing import Dict, Any
from telegram import Bot, Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging for CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS services (optional for basic functionality)
try:
    dynamodb = boto3.resource('dynamodb')
except Exception:
    dynamodb = None  # DynamoDB optional for basic bot functionality

# Global bot instance (cached between Lambda invocations)
bot_instance = None

def get_bot_token() -> str:
    """Retrieve bot token from environment variable"""
    token = os.getenv('BOT_TOKEN', '')
    if not token:
        raise ValueError("BOT_TOKEN environment variable not found")
    return token

def get_bot() -> Bot:
    """Get or create cached bot instance"""
    global bot_instance
    if bot_instance is None:
        token = get_bot_token()
        if not token:
            raise ValueError("Bot token not found in Parameter Store or environment")
        bot_instance = Bot(token=token)
    return bot_instance

# Command handlers - matching current telegram_bot.py functionality
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    
    # Store user info in DynamoDB for future use (optional, non-blocking)
    if dynamodb:
        try:
            table_name = os.environ.get('USERS_TABLE_NAME', 'aihelper-users-dev')
            table = dynamodb.Table(table_name)
            table.put_item(Item={
                'user_id': user.id,
                'username': user.username or '',
                'first_name': user.first_name or '',
                'joined_at': str(update.message.date),
                'active': True
            })
            logger.info(f"User {user.id} registered/updated in database")
        except Exception as e:
            logger.error(f"Failed to store user data: {e}")
            # Don't fail the command if database is unavailable
    
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for Telegram webhook
    
    This function receives webhook calls from Telegram via API Gateway
    and processes them using the python-telegram-bot library
    """
    try:
        # Log the incoming event for debugging
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse the webhook payload
        if 'body' not in event:
            logger.error("No body in event")
            return {'statusCode': 400, 'body': 'Bad Request'}
        
        # Handle both API Gateway formats (v1 and v2)
        body = event['body']
        if isinstance(body, str):
            body = json.loads(body)
        
        # Create Update object from webhook data
        update = Update.de_json(body, get_bot())
        
        if not update:
            logger.error("Could not parse update from webhook")
            return {'statusCode': 400, 'body': 'Invalid update'}
        
        # Create application instance for handling the update
        application = Application.builder().token(get_bot_token()).build()
        
        # Register handlers - matching current telegram_bot.py
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        # Process the update
        import asyncio
        asyncio.run(application.process_update(update))
        
        logger.info("Update processed successfully")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Update processed'})
        }
        
    except Exception as e:
        logger.error(f"Error processing update: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

# For local testing
if __name__ == "__main__":
    import os
    # Set environment variables for local testing
    os.environ['BOT_TOKEN'] = 'your_bot_token_here'
    os.environ['USERS_TABLE_NAME'] = 'aihelper-users-dev'
    
    # Test event simulation for /start command
    test_start_event = {
        "body": json.dumps({
            "update_id": 123,
            "message": {
                "message_id": 456,
                "date": 1640995200,
                "text": "/start",
                "from": {
                    "id": 12345,
                    "username": "testuser",
                    "first_name": "Test"
                },
                "chat": {
                    "id": 12345,
                    "type": "private"
                }
            }
        })
    }
    
    # Test event simulation for echo message
    test_echo_event = {
        "body": json.dumps({
            "update_id": 124,
            "message": {
                "message_id": 457,
                "date": 1640995300,
                "text": "Hello bot!",
                "from": {
                    "id": 12345,
                    "username": "testuser",
                    "first_name": "Test"
                },
                "chat": {
                    "id": 12345,
                    "type": "private"
                }
            }
        })
    }
    
    print("Testing /start command:")
    result1 = lambda_handler(test_start_event, None)
    print(f"Start command result: {result1}")
    
    print("\nTesting echo functionality:")
    result2 = lambda_handler(test_echo_event, None)
    print(f"Echo result: {result2}")
