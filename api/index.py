"""Simple Vercel serverless function without Flask."""
import json
import traceback

def handler(event, context):
    """Handle Vercel requests."""
    try:
        # Log the event for debugging
        print(f"Event: {json.dumps(event)}")
        
        # Get path from event - Vercel may pass it differently
        path = '/'
        if isinstance(event, dict):
            # Try different ways Vercel might pass the path
            path = event.get('path', '') or event.get('rawPath', '') or event.get('requestContext', {}).get('http', {}).get('path', '/')
        
        # Ensure path is not empty
        if not path:
            path = '/'
        
        print(f"Path: {path}")
        
        if path == '/' or path == '':
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'text/html'},
                'body': '''<!DOCTYPE html>
<html>
<head><title>Oracle Agent</title></head>
<body style="font-family:Arial;text-align:center;padding:50px;background:linear-gradient(135deg,#667eea,#764ba2);color:white">
    <h1>🚀 Oracle Agent</h1>
    <h2 style="color:#4CAF50">✅ Working!</h2>
    <p>Vercel deployment successful</p>
</body>
</html>'''
            }
        
        if path == '/api/health' or path.startswith('/api/health'):
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({"status":"healthy","service":"oracle-agent"})
            }
        
        if path == '/api/status' or path.startswith('/api/status'):
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({"status":"online","version":"5.0.0"})
            }
        
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'text/plain'},
            'body': f'Not Found: {path}'
        }
    except Exception as e:
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/plain'},
            'body': error_msg
        }

# For Vercel compatibility
main = handler
lambda_handler = handler
