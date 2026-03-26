"""Simple Vercel serverless function without Flask."""

def handler(event, context):
    """Handle Vercel requests."""
    path = event.get('path', '/')
    
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
    
    if path == '/api/health':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': '{"status":"healthy","service":"oracle-agent"}'
        }
    
    if path == '/api/status':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': '{"status":"online","version":"5.0.0-hardened"}'
        }
    
    return {
        'statusCode': 404,
        'headers': {'Content-Type': 'text/plain'},
        'body': 'Not Found'
    }

# For Vercel compatibility
main = handler
lambda_handler = handler
