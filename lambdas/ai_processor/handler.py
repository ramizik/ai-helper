import json
import logging
import os
from typing import Dict, Any
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')

def get_openai_api_key() -> str:
    """Retrieve OpenAI API key from AWS Secrets Manager"""
    try:
        secret_name = os.environ.get('OPENAI_API_SECRET')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])
        return secret_data.get('api_key', '')
    except Exception as e:
        logger.error(f"Failed to retrieve OpenAI API key: {e}")
        return ""

def process_ai_request(user_id: int, request_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Process AI request based on type and context"""
    try:
        # TODO: Implement LangChain integration
        # For now, return a placeholder response
        if request_type == "morning_summary":
            return {
                "type": "morning_summary",
                "content": "Good morning! Here's your daily summary...",
                "timestamp": context.get("timestamp", ""),
                "user_id": user_id
            }
        elif request_type == "event_reminder":
            return {
                "type": "event_reminder",
                "content": f"Reminder: {context.get('event_title', 'Upcoming event')}",
                "timestamp": context.get("timestamp", ""),
                "user_id": user_id
            }
        else:
            return {
                "type": "general",
                "content": "AI processing request...",
                "timestamp": context.get("timestamp", ""),
                "user_id": user_id
            }
    except Exception as e:
        logger.error(f"Error processing AI request: {e}")
        return {
            "type": "error",
            "content": "Sorry, I encountered an error processing your request.",
            "timestamp": context.get("timestamp", ""),
            "user_id": user_id
        }

def store_ai_memory(memory_data: Dict[str, Any]) -> bool:
    """Store AI memory in DynamoDB"""
    try:
        table_name = os.environ.get('AI_MEMORY_TABLE')
        table = dynamodb.Table(table_name)
        
        # Add timestamp if not present
        if 'timestamp' not in memory_data:
            import datetime
            memory_data['timestamp'] = datetime.datetime.utcnow().isoformat()
        
        # Add TTL (7 days from now)
        import datetime
        memory_data['ttl'] = int((datetime.datetime.utcnow() + datetime.timedelta(days=7)).timestamp())
        
        table.put_item(Item=memory_data)
        logger.info(f"Stored AI memory: {memory_data.get('memory_id', 'unknown')}")
        return True
    except Exception as e:
        logger.error(f"Failed to store AI memory: {e}")
        return False

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for AI processing"""
    try:
        logger.info(f"AI Processor received event: {json.dumps(event)}")
        
        # Extract event details
        event_type = event.get('detail-type', 'unknown')
        user_id = event.get('detail', {}).get('user_id')
        request_type = event.get('detail', {}).get('request_type', 'general')
        context_data = event.get('detail', {}).get('context', {})
        
        # Process the AI request
        result = process_ai_request(user_id, request_type, context_data)
        
        # Store the result in AI memory
        if result.get('type') != 'error':
            memory_data = {
                'memory_id': f"ai_{event_type}_{user_id}_{int(context.time_remaining() / 1000)}",
                'user_id': user_id,
                'request_type': request_type,
                'result': result,
                'context': context_data
            }
            store_ai_memory(memory_data)
        
        logger.info(f"AI processing completed: {result.get('type')}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'result': result
            })
        }
        
    except Exception as e:
        logger.error(f"AI Processor error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
