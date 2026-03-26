"""Vercel serverless function for Oracle Agent."""

def handler(request):
    """Vercel serverless function."""
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': '''
<!DOCTYPE html>
<html>
<head>
    <title>Oracle Agent - Vercel Deployment</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            text-align: center; 
            padding: 50px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container { 
            max-width: 800px; 
            margin: 0 auto; 
        }
        .status { 
            background: rgba(76, 175, 80, 0.2); 
            border: 1px solid rgba(76, 175, 80, 0.5); 
            border-radius: 10px; 
            padding: 20px; 
            margin: 20px 0; 
        }
        h1 { font-size: 3em; margin-bottom: 20px; }
        h2 { color: #4CAF50; }
        .info { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Oracle Agent</h1>
        <div class="status">
            <h2>✅ Vercel Deployment Successful!</h2>
            <p>Oracle Agent is running on Vercel serverless platform</p>
            <div class="info">
                <p><strong>Status:</strong> Function Handler Working</p>
                <p><strong>Runtime:</strong> Python Serverless</p>
                <p><strong>Method:</strong> Simple Function (No Class)</p>
                <p><strong>Request Path:</strong> ''' + str(request.get('path', '/')) + '''</p>
                <p><strong>Method:</strong> ''' + str(request.get('method', 'GET')) + '''</p>
            </div>
        </div>
    </div>
</body>
</html>
        '''
    }

# Export for Vercel
__all__ = ['handler']
