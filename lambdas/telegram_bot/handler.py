"""
Telegram Bot Lambda - AI Assistant Bot
Handles user interactions and provides AI-powered responses
"""

import json
import logging
import os
import boto3
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Tuple
import uuid

# Third-party imports
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS services
try:
    dynamodb = boto3.resource('dynamodb')
    logger.info("DynamoDB initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize DynamoDB: {e}")
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
                # Secret is stored as plain string, not JSON
                token = response['SecretString']
                
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

# ===== Tasks helpers =====

def get_tasks_table_name() -> str:
    return os.environ.get('TASKS_TABLE', 'aihelper-tasks-dev')

def get_tasks_table():
    if not dynamodb:
        raise RuntimeError("DynamoDB is not initialized")
    return dynamodb.Table(get_tasks_table_name())

def find_task_by_name(user_id: int, task_name: str) -> Tuple[List[Dict[str, Any]], str]:
    """Find tasks by name, returns (matching_tasks, error_message)"""
    try:
        table = get_tasks_table()
        resp = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id) &
                                  boto3.dynamodb.conditions.Key('sort_key').begins_with('task#')
        )
        matching_tasks = [item for item in resp.get('Items', []) if item.get('name', '').lower() == task_name.lower()]
        
        if not matching_tasks:
            return [], f"Task '{task_name}' not found."
        if len(matching_tasks) > 1:
            return [], f"Multiple tasks found with name '{task_name}'. Please be more specific."
        
        return matching_tasks, ""
    except Exception as e:
        logger.error(f"find_task_by_name error: {e}")
        return [], f"Error finding task: {str(e)}"

def parse_task_args(text: str) -> Tuple[str, Optional[int], Optional[str]]:
    """Parse task arguments like: "TaskName 5 0428" -> (name, priority, due_date)"""
    parts = text.strip().split()
    if not parts:
        return "", None, None
    
    name = parts[0]
    priority: Optional[int] = None
    due_date: Optional[str] = None
    
    # Parse priority (second argument)
    if len(parts) > 1:
        try:
            p = int(parts[1])
            if 1 <= p <= 5:
                priority = p
        except ValueError:
            pass
    
    # Parse due date (third argument) - format: MMDD
    if len(parts) > 2:
        date_part = parts[2]
        if len(date_part) == 4 and date_part.isdigit():
            month = date_part[:2]
            day = date_part[2:]
            try:
                # Validate month and day
                if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                    # Use current year
                    current_year = datetime.utcnow().year
                    due_date = f"{current_year}-{month}-{day}"
                    # Validate the full date
                    datetime.strptime(due_date, '%Y-%m-%d')
                else:
                    due_date = None
            except ValueError:
                due_date = None
    
    return name, priority, due_date

async def t_add(update: Update, context: Any) -> None:
    """/t-add "TaskName 5 0428" - Add task with priority 5, due April 28"""
    try:
        user = update.effective_user
        args_text = update.message.text[len('/t-add'):].strip()
        if not args_text:
            await update.message.reply_text('Usage: /t-add "TaskName 5 0428" (priority and due date optional)')
            return
        
        # Remove quotes if present
        if args_text.startswith('"') and args_text.endswith('"'):
            args_text = args_text[1:-1]
        
        name, priority, due_date = parse_task_args(args_text)
        if not name:
            await update.message.reply_text("Please provide a task name")
            return
            
        task_id = str(uuid.uuid4())
        added_date = datetime.utcnow().strftime('%Y-%m-%d')
        sort_key = f"task#{task_id}"
        item = {
            'user_id': user.id,
            'sort_key': sort_key,
            'task_id': task_id,
            'name': name,
            'added_date': added_date,
            'priority': priority if priority is not None else -1,
            'status': 'incomplete',
            'due_date': due_date if due_date else '',
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        table = get_tasks_table()
        table.put_item(Item=item)
        
        # Build confirmation message
        msg = f"✅ Task added: {name}"
        if priority:
            msg += f" (Priority: {priority})"
        if due_date:
            msg += f" (Due: {due_date})"
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"t_add error: {e}")
        await update.message.reply_text("❌ Failed to add task. Please try again.")

async def t_edit(update: Update, context: Any) -> None:
    """/t-edit "TaskName 5 0428" - Edit task with new priority 5, due April 28"""
    try:
        user = update.effective_user
        args_text = update.message.text[len('/t-edit'):].strip()
        if not args_text:
            await update.message.reply_text('Usage: /t-edit "TaskName 5 0428" (priority and due date optional)')
            return
        
        # Remove quotes if present
        if args_text.startswith('"') and args_text.endswith('"'):
            args_text = args_text[1:-1]
        
        parts = args_text.split()
        if len(parts) < 1:
            await update.message.reply_text("Please provide a task name to edit")
            return
        
        task_name = parts[0]
        updates: Dict[str, Any] = {}
        
        # Parse priority (second argument)
        if len(parts) > 1:
            try:
                p = int(parts[1])
                if 1 <= p <= 5:
                    updates['priority'] = p
            except ValueError:
                pass
        
        # Parse due date (third argument) - format: MMDD
        if len(parts) > 2:
            date_part = parts[2]
            if len(date_part) == 4 and date_part.isdigit():
                month = date_part[:2]
                day = date_part[2:]
                try:
                    if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                        current_year = datetime.utcnow().year
                        due_date = f"{current_year}-{month}-{day}"
                        datetime.strptime(due_date, '%Y-%m-%d')
                        updates['due_date'] = due_date
                except ValueError:
                    pass
        
        if not updates:
            await update.message.reply_text("No valid fields to update. Provide priority (1-5) and/or due date (MMDD)")
            return
        
        # Find task by name
        matching_tasks, error_msg = find_task_by_name(user.id, task_name)
        if error_msg:
            await update.message.reply_text(error_msg)
            return
        
        item = matching_tasks[0]
        item.update(updates)
        item['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        table = get_tasks_table()
        table.put_item(Item=item)
        
        # Build confirmation message
        msg = f"✅ Task '{task_name}' updated"
        if 'priority' in updates:
            msg += f" (Priority: {updates['priority']})"
        if 'due_date' in updates:
            msg += f" (Due: {updates['due_date']})"
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"t_edit error: {e}")
        await update.message.reply_text("❌ Failed to edit task.")

async def t_complete(update: Update, context: Any) -> None:
    """/t-complete TaskName - Mark task as complete"""
    try:
        user = update.effective_user
        task_name = update.message.text[len('/t-complete'):].strip()
        if not task_name:
            await update.message.reply_text("Usage: /t-complete TaskName")
            return
        
        # Find task by name
        matching_tasks, error_msg = find_task_by_name(user.id, task_name)
        if error_msg:
            await update.message.reply_text(error_msg)
            return
        
        item = matching_tasks[0]
        item['status'] = 'complete'
        item['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        table = get_tasks_table()
        table.put_item(Item=item)
        await update.message.reply_text(f"✅ Task '{task_name}' marked complete.")
    except Exception as e:
        logger.error(f"t_complete error: {e}")
        await update.message.reply_text("❌ Failed to complete task.")

async def t_delete(update: Update, context: Any) -> None:
    """/t-delete TaskName - Delete task"""
    try:
        user = update.effective_user
        task_name = update.message.text[len('/t-delete'):].strip()
        if not task_name:
            await update.message.reply_text("Usage: /t-delete TaskName")
            return
        
        # Find task by name
        matching_tasks, error_msg = find_task_by_name(user.id, task_name)
        if error_msg:
            await update.message.reply_text(error_msg)
            return
        
        item = matching_tasks[0]
        table = get_tasks_table()
        table.delete_item(Key={'user_id': user.id, 'sort_key': item['sort_key']})
        await update.message.reply_text(f"🗑️ Task '{task_name}' deleted.")
    except Exception as e:
        logger.error(f"t_delete error: {e}")
        await update.message.reply_text("❌ Failed to delete task.")

def format_task_line(item: Dict[str, Any]) -> str:
    prio = item.get('priority', -1)
    prio_txt = f"P{prio}" if isinstance(prio, int) and prio in (1,2,3,4,5) else "P-"
    due = item.get('due_date') or '-'
    status = '✅' if item.get('status') == 'complete' else '⬜'
    name = item.get('name', 'Unnamed')
    return f"{status} [{prio_txt}] {name} (due: {due})"

async def t_list(update: Update, context: Any) -> None:
    """/t-list - list incomplete tasks; /t-all for all"""
    try:
        user = update.effective_user
        table = get_tasks_table()
        # Scan user's tasks (PK + begins_with on sort_key 'task#' requires FilterExpression when PK known)
        resp = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user.id) &
                                  boto3.dynamodb.conditions.Key('sort_key').begins_with('task#')
        )
        items = resp.get('Items', [])
        show_all = update.message.text.strip().startswith('/t-all')
        if not show_all:
            items = [i for i in items if i.get('status') != 'complete']
        # Sort by priority desc then due_date asc then added_date asc
        def sort_key_fn(i: Dict[str, Any]):
            pr = i.get('priority', -1)
            pr = pr if isinstance(pr, int) else -1
            dd = i.get('due_date') or '9999-12-31'
            ad = i.get('added_date', '9999-12-31')
            return (-pr, dd, ad)
        items.sort(key=sort_key_fn)
        if not items:
            await update.message.reply_text("No tasks found.")
            return
        lines = [format_task_line(i) for i in items]
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        logger.error(f"t_list error: {e}")
        await update.message.reply_text("❌ Failed to list tasks.")

async def t_today(update: Update, context: Any) -> None:
    """/t-today - tasks due today and incomplete"""
    try:
        user = update.effective_user
        table = get_tasks_table()
        today_str = date.today().strftime('%Y-%m-%d')
        # Query GSI by due_date
        resp = table.query(
            IndexName='DueDateIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user.id) &
                                  boto3.dynamodb.conditions.Key('due_date').eq(today_str)
        )
        items = [i for i in resp.get('Items', []) if i.get('status') != 'complete']
        if not items:
            await update.message.reply_text("No tasks due today. 🎉")
            return
        # Sort by priority desc
        items.sort(key=lambda i: (-(i.get('priority') or -1)))
        lines = [format_task_line(i) for i in items]
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        logger.error(f"t_today error: {e}")
        await update.message.reply_text("❌ Failed to fetch today's tasks.")

async def t_pending(update: Update, context: Any) -> None:
    """/t-pending - all incomplete tasks regardless of due date"""
    try:
        user = update.effective_user
        table = get_tasks_table()
        resp = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user.id) &
                                  boto3.dynamodb.conditions.Key('sort_key').begins_with('task#')
        )
        items = [i for i in resp.get('Items', []) if i.get('status') != 'complete']
        if not items:
            await update.message.reply_text("No pending tasks. 🎉")
            return
        items.sort(key=lambda i: (-(i.get('priority') or -1), i.get('due_date') or '9999-12-31'))
        lines = [format_task_line(i) for i in items]
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        logger.error(f"t_pending error: {e}")
        await update.message.reply_text("❌ Failed to fetch pending tasks.")

# ===== Existing commands =====

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
                
                # Check if user profile already exists
                existing = table.get_item(
                    Key={
                        'user_id': user.id,
                        'sort_key': 'profile'
                    }
                )
                
                if 'Item' not in existing:
                    # Create new profile
                    table.put_item(Item=user_item)
                    logger.info(f"New user profile created: {user.id}")
                else:
                    # Update existing profile
                    user_item['updated_at'] = datetime.utcnow().isoformat() + 'Z'
                    table.put_item(Item=user_item)
                    logger.info(f"User profile updated: {user.id}")
                    
            except Exception as e:
                logger.error(f"Failed to store user profile: {e}")
                # Continue with bot functionality even if DB fails

async def help_command(update: Update, context: Any) -> None:
    """Handle /help command"""
    help_text = (
        "🤖 **AI Assistant Commands**\n\n"
        "**Basic Commands:**\n"
        "/start - Start the bot and get welcome message\n"
        "/help - Show this help message\n"
        "\n**Tasks:**\n"
        "/t-add \"TaskName 5 0428\" - Add task with priority 5, due April 28\n"
        "/t-edit \"TaskName 3 0501\" - Edit task priority to 3, due May 1\n"
        "/t-complete TaskName - Mark task complete\n"
        "/t-delete TaskName - Delete task\n"
        "/t-list - List incomplete tasks (sorted by priority/due)\n"
        "/t-all - List all tasks\n"
        "/t-today - Tasks due today (incomplete)\n"
        "/t-pending - All incomplete tasks\n"
        "\n**Calendar Commands:**\n"
        "/calendar - Show today's calendar events\n"
        "/next - Show next upcoming event\n"
        "/sync - Manually sync calendar (admin only)\n"
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
        "Try /help to see available commands."
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
        
        # Get bot instance first
        bot = get_bot()
        
        # Parse the Telegram update with bot instance
        try:
            update_data = json.loads(event['body'])
            update = Update.de_json(update_data, bot)
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
            
            try:
                text = update.message.text.strip()
                if text.startswith('/start'):
                    await start_command(update, context)
                elif text.startswith('/help'):
                    await help_command(update, context)
                # Task commands
                elif text.startswith('/t-add'):
                    await t_add(update, context)
                elif text.startswith('/t-edit'):
                    await t_edit(update, context)
                elif text.startswith('/t-complete'):
                    await t_complete(update, context)
                elif text.startswith('/t-delete'):
                    await t_delete(update, context)
                elif text.startswith('/t-today'):
                    await t_today(update, context)
                elif text.startswith('/t-pending'):
                    await t_pending(update, context)
                elif text.startswith('/t-all') or text.startswith('/t-list'):
                    await t_list(update, context)
                else:
                    await echo(update, context)
                
                logger.info(f"Bot processed message for {user.id} successfully")
            except Exception as e:
                logger.error(f"Error processing command for user {user.id}: {e}")
                # Try to send error message to user
                try:
                    await update.message.reply_text("Sorry, I encountered an error processing your request. Please try again.")
                except Exception as reply_error:
                    logger.error(f"Failed to send error reply: {reply_error}")
        
        return {'statusCode': 200, 'body': 'OK'}
        
    except Exception as e:
        logger.error(f"Error processing update: {str(e)}")
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous wrapper for AWS Lambda compatibility"""
    import asyncio
    try:
        # Create new event loop for this invocation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the async handler and get the result
        result = loop.run_until_complete(lambda_handler_async(event, context))
        
        # Clean up
        loop.close()
        
        # Ensure result is a dict, not a coroutine
        if asyncio.iscoroutine(result):
            logger.error("Handler returned coroutine instead of result")
            return {'statusCode': 500, 'body': json.dumps({'error': 'Handler returned coroutine'})}
        
        return result
        
    except Exception as e:
        logger.error(f"Error in lambda_handler wrapper: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
    finally:
        # Ensure loop is always closed
        try:
            if 'loop' in locals() and not loop.is_closed():
                loop.close()
        except:
            pass
