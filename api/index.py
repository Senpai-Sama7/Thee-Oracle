"""Vercel serverless function for Oracle Agent."""

from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler class."""
    
    def do_GET(self):
        """Handle GET requests."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html_content = '''
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
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Oracle Agent</h1>
        <div class="status">
            <h2>✅ Vercel Deployment Successful!</h2>
            <p>Oracle Agent is running on Vercel serverless platform</p>
            <p><strong>Status:</strong> Function Handler Working</p>
            <p><strong>Runtime:</strong> Python Serverless</p>
            <p><strong>URL:</strong> ''' + self.path + '''</p>
        </div>
    </div>
</body>
</html>
        '''
        
        self.wfile.write(html_content.encode('utf-8'))
    
    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            'success': True,
            'message': 'Oracle Agent received your POST request',
            'path': self.path,
            'method': 'POST',
            'data_length': content_length,
            'timestamp': '2026-03-25T12:00:00Z'
        }
        
        self.wfile.write(json.dumps(response).encode('utf-8'))

# Vercel compatibility - export the handler class
__all__ = ['handler']
