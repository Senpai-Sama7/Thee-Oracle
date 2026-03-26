"""Vercel serverless function for Oracle Agent."""

def handler(request):
    """Handle Vercel serverless function requests."""
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': '''
<!DOCTYPE html>
<html>
<head>
    <title>Oracle Agent - Vercel Deployment</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        .container { max-width: 800px; margin: 0 auto; }
        .status { background: #4CAF50; color: white; padding: 20px; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Oracle Agent</h1>
        <div class="status">
            <h2>✅ Vercel Deployment Successful!</h2>
            <p>Oracle Agent is running on Vercel serverless platform</p>
        </div>
        <p>Serverless function is working correctly</p>
    </div>
</body>
</html>
        '''
    }
