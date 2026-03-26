"""Vercel serverless function for Oracle Agent."""

def handler(event=None, context=None):
    """Vercel serverless function - simplest possible version."""
    html_content = '''
<!DOCTYPE html>
<html>
<head>
    <title>Oracle Agent - Vercel Deployment</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            text-align: center; 
            padding: 50px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            margin: 0;
        }
        .container { 
            max-width: 800px; 
            margin: 0 auto; 
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .status { 
            background: rgba(76, 175, 80, 0.2); 
            border-radius: 10px; 
            padding: 20px; 
            margin: 20px 0; 
        }
        h1 { font-size: 3em; margin-bottom: 20px; text-shadow: 0 2px 4px rgba(0,0,0,0.3); }
        h2 { color: #4CAF50; margin-bottom: 15px; }
        .success { color: #4CAF50; font-size: 1.2em; }
        .url { 
            background: rgba(0,0,0,0.3); 
            padding: 10px; 
            border-radius: 5px; 
            margin: 10px 0;
            word-break: break-all;
        }
        .features {
            text-align: left;
            margin: 20px 0;
        }
        .feature {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Oracle Agent</h1>
        <div class="status">
            <h2>✅ Vercel Deployment Successful!</h2>
            <p class="success">Serverless function is working correctly!</p>
        </div>
        
        <div class="features">
            <h3>🎯 What's Working:</h3>
            <div class="feature">
                <strong>✅ Serverless Function:</strong> Python runtime active
            </div>
            <div class="feature">
                <strong>✅ Build System:</strong> Vercel build successful
            </div>
            <div class="feature">
                <strong>✅ Routing:</strong> Routes configured
            </div>
            <div class="feature">
                <strong>✅ Deployment:</strong> Production ready
            </div>
        </div>
        
        <div class="url">
            <h3>🌐 Access URLs:</h3>
            <div class="feature">
                <strong>Main:</strong> https://thee-oracle.vercel.app
            </div>
            <div class="feature">
                <strong>API:</strong> https://thee-oracle.vercel.app/api/test
            </div>
        </div>
        
        <div class="status">
            <h3>🛠️ Next Steps:</h3>
            <p>1. Test the API endpoint</p>
            <p>2. Add more functionality</p>
            <p>3. Integrate with Oracle Agent core</p>
        </div>
    </div>
</body>
</html>
    '''
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html; charset=utf-8',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
        },
        'body': html_content
    }

# Test endpoint
def api_test(event=None, context=None):
    """API test endpoint."""
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': '{"success": true, "message": "Oracle Agent API is working!", "service": "oracle-agent-vercel", "version": "5.0.0-hardened"}'
    }

# Vercel compatibility
def main(event=None, context=None):
    """Main entry point."""
    return handler(event, context)

def lambda_handler(event=None, context=None):
    """Lambda-style entry point."""
    return handler(event, context)

# Export all possible entry points
__all__ = ['handler', 'main', 'lambda_handler', 'api_test']
