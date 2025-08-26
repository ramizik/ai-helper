"""
Telegram Bot Lambda - AI Assistant Bot
Handles user interactions and provides AI-powered responses
"""

import json
import logging
import os
import boto3
from datetime import datetime
from typing import Dict, Any

# Third-party imports
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS services
dynamodb = None  # DynamoDB optional for basic bot functionality

def get_bot_token() -> str:
    """Retrieve bot token from AWS Secrets Manager or fallback to environment"""
    try:
        # First, try to get from AWS Secrets Manager
        if 'BOT_TOKEN_SECRET' in os.environ:
            secrets_client = boto3.client('secretsmanager')
            secret_name = os.environ['BOT_TOKEN_SECRET']
            
            try:
                response = secrets_client.get_secret_value(SecretId=secret_name)
                secret_data = json.loads(response['SecretString'])
                token = secret_data.get('bot_token') or secret_data.get('BOT_TOKEN')
                
                if token:
                    logger.info("Retrieved bot token from AWS Secrets Manager")
                    return token
                else:
                    logger.warning("Bot token not found in secret data")
            except Exception as e:
                logger.warning(f"Failed to retrieve from Secrets Manager: {e}")
        
        # Fallback to environment variable (for local development)
        token = os.getenv('BOT_TOKEN', '')
        if token:
            logger.info("Using bot token from environment variable")
            return token
        
        raise ValueError("Bot token not found in Secrets Manager or environment")
        
    except Exception as e:
        logger.error(f"Failed to get bot token: {e}")
        raise

def get_bot() -> Bot:
    """Create a fresh bot instance for each Lambda invocation"""
    token = get_bot_token()
    if not token:
        raise ValueError("Bot token not found")
    
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(
        pool_timeout=5.0,
        connection_pool_size=1,
        read_timeout=10.0,
        write_timeout=10.0,
        connect_timeout=5.0
    )
    return Bot(token=token, request=request)

async def start_command(update: Update, context: Any) -> None:
    """Handle /start command"""
    user = update.effective_user
    welcome_message = (
        f"👋 Hello {user.first_name}! I'm your AI personal assistant.\n\n"
        "I can help you with:\n"
        "• 📅 Calendar management and reminders\n"
        "• 🧠 AI-powered insights and summaries\n"
        "• ⏰ Proactive notifications\n"
        "• 💬 General conversation and assistance\n\n"
        "Use /help to see all available commands!"
    )
    
    await update.message.reply_text(welcome_message)
    
    # Store user info in DynamoDB if available
    if dynamodb:
        try:
            table_name = os.environ.get('USERS_TABLE', 'aihelper-users-dev')
            table = dynamodb.Table(table_name)
            
            # Create user profile
            user_item = {
                'user_id': user.id,
                'sort_key': 'profile',
                'first_name': user.first_name,
                'username': user.username,
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'updated_at': datetime.utcnow().isoformat() + 'Z'
            }
            
            table.put_item(Item=user_item)
            logger.info(f"User profile stored: {user.id}")
            
        except Exception as e:
            logger.error(f"Failed to store user profile: {e}")

async def help_command(update: Update, context: Any) -> None:
    """Handle /help command"""
    help_text = (
        "🤖 **AI Assistant Commands**\n\n"
        "**Basic Commands:**\n"
        "/start - Start the bot and get welcome message\n"
        "/help - Show this help message\n"
        "/status - Check your current status and upcoming events\n\n"
        "**Calendar Commands:**\n"
        "/calendar - Show today's calendar events\n"
        "/next - Show next upcoming event\n"
        "/sync - Manually sync calendar (admin only)\n\n"
        "**AI Commands:**\n"
        "/summary - Get AI-generated daily summary\n"
        "/insights - Get AI insights about your schedule\n"
        "/suggest - Get AI suggestions for time management\n\n"
        "**Settings:**\n"
        "/preferences - Manage notification preferences\n"
        "/timezone - Set your timezone\n\n"
        "Just send me a message and I'll respond naturally! 🚀"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def echo(update: Update, context: Any) -> None:
    """Handle regular messages with AI processing"""
    user = update.effective_user
    message_text = update.message.text
    
    # For now, provide a helpful response
    # TODO: Integrate with AI Processor for intelligent responses
    response = (
        f"💬 Thanks for your message: \"{message_text}\"\n\n"
        "I'm currently learning to be more helpful! Soon I'll be able to:\n"
        "• 📊 Analyze your calendar and provide insights\n"
        "• 🎯 Help you stay on track with your goals\n"
        "• ⏰ Send proactive reminders and suggestions\n"
        "• 🧠 Have intelligent conversations about your schedule\n\n"
        "For now, try /help to see what I can do! 🚀"
    )
    
    await update.message.reply_text(response)

async def log_message_to_db(user_id: int, message: str, sender: str, timestamp) -> None:
    """Log message to DynamoDB for conversation history"""
    if not dynamodb:
        return
    
    try:
        table_name = os.environ.get('USERS_TABLE', 'aihelper-users-dev')
        table = dynamodb.Table(table_name)
        
        # Create sort key for message
        sort_key = f"message_{int(timestamp.timestamp())}_{sender}"
        
        table.put_item(Item={
            'user_id': user_id,
            'sort_key': sort_key,
            'message': message,
            'sender': sender,
            'timestamp': str(timestamp),
            'date': timestamp.strftime('%Y-%m-%d'),
            'time': timestamp.strftime('%H:%M:%S')
        })
        logger.info(f"Message logged to DB: {sender} -> {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to log message to DB: {e}")

async def lambda_handler_async(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Async Lambda handler for Telegram Bot"""
    try:
        # Parse the incoming webhook event
        if 'body' not in event:
            return {'statusCode': 400, 'body': 'No body in event'}
        
        # Parse the Telegram update
        try:
            update_data = json.loads(event['body'])
            update = Update.de_json(update_data, None)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {'statusCode': 400, 'body': 'Invalid JSON'}
        
        # Process the update
        if update.message and update.message.text:
            user = update.effective_user
            message_text = update.message.text
            logger.info(f"User {user.id} ({user.first_name}): {message_text}")
            
            # Log user message
            await log_message_to_db(user.id, message_text, "user", update.message.date)
            
            # Route to appropriate handler
            if update.message.text.startswith('/start'):
                await start_command(update, context)
            elif update.message.text.startswith('/help'):
                await help_command(update, context)
            else:
                await echo(update, context)
            
            logger.info(f"Bot processed message for {user.id}")
        
        return {'statusCode': 200, 'body': 'OK'}
        
    except Exception as e:
        logger.error(f"Error processing update: {str(e)}")
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous wrapper for AWS Lambda compatibility"""
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(lambda_handler_async(event, context))
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Error in lambda_handler wrapper: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
