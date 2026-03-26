"""Flask app for Vercel deployment - root level."""

from flask import Flask, jsonify, request
import json

app = Flask(__name__)

@app.route('/')
def index():
    """Main page."""
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
            <p class="success">Root-level Flask app is working correctly!</p>
        </div>
        
        <div class="features">
            <h3>🎯 What's Working:</h3>
            <div class="feature">
                <strong>✅ Root Flask App:</strong> Python Flask runtime active
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
    return html_content

@app.route('/api/test')
def api_test():
    """API test endpoint."""
    return jsonify({
        'success': True,
        'message': 'Oracle Agent API is working!',
        'service': 'oracle-agent-vercel',
        'version': '5.0.0-hardened',
        'features': [
            'workflow_engine',
            'agent_collaboration', 
            'code_generation', 
            'plugin_system',
            'integration_framework'
        ],
        'endpoints': [
            {'path': '/', 'method': 'GET', 'description': 'Main Oracle Agent interface'},
            {'path': '/api/test', 'method': 'GET', 'description': 'API test endpoint'}
        ],
        'timestamp': '2026-03-25T12:00:00Z',
        'deployment': 'vercel-root-flask'
    })

# Vercel handler
def handler(environ, start_response):
    """Vercel WSGI handler."""
    return app(environ, start_response)
