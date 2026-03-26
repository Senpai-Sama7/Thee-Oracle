"""Vercel serverless function entrypoint for Oracle Agent GUI."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables for Vercel
os.environ.setdefault('ORACLE_DEMO_MODE', 'true')
os.environ.setdefault('FORCE_HTTPS', 'false')

# Import the Vercel-compatible Flask app
from vercel_app import app

class VercelWSGIAdapter:
    """Adapter to convert Vercel request to WSGI format."""
    
    def __init__(self, flask_app):
        self.flask_app = flask_app
    
    def __call__(self, request):
        """Handle Vercel request and return response."""
        try:
            # Convert Vercel request to WSGI environ
            environ = self._create_wsgi_environ(request)
            
            # Capture response
            response_data = {}
            def start_response(status, headers):
                response_data['status'] = status
                response_data['headers'] = headers
            
            # Get WSGI response
            result = self.flask_app(environ, start_response)
            
            # Convert to Vercel response
            return self._create_vercel_response(result, response_data)
            
        except Exception as e:
            # Return error response
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': '{"error": "Internal server error", "message": "' + str(e) + '"}'
            }
    
    def _create_wsgi_environ(self, request):
        """Create WSGI environ from Vercel request."""
        method = request.get('method', 'GET')
        url = request.get('url', '/')
        headers = request.get('headers', {})
        query = request.get('query', {})
        body = request.get('body', '')
        
        # Parse URL
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(url)
        path_info = parsed_url.path
        query_string = parsed_url.query
        
        # Build WSGI environ
        environ = {
            'REQUEST_METHOD': method,
            'PATH_INFO': path_info,
            'QUERY_STRING': query_string,
            'SERVER_NAME': 'vercel.app',
            'SERVER_PORT': '443',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'https',
            'wsgi.input': type('', (), {'read': lambda: body.encode() if body else b''})(),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': True,
        }
        
        # Add headers
        for key, value in headers.items():
            key = key.upper().replace('-', '_')
            if key not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                key = f'HTTP_{key}'
            environ[key] = value
        
        # Add query parameters
        for key, values in query.items():
            environ[f'QUERY_{key.upper()}'] = values[0] if values else ''
        
        # Add body content
        if body:
            environ['CONTENT_LENGTH'] = str(len(body))
            if 'CONTENT_TYPE' not in environ:
                environ['CONTENT_TYPE'] = 'application/json'
        
        return environ
    
    def _create_vercel_response(self, wsgi_result, response_data):
        """Convert WSGI response to Vercel format."""
        # Get response body
        body = b''
        for chunk in wsgi_result:
            if isinstance(chunk, str):
                body += chunk.encode('utf-8')
            else:
                body += chunk
        
        # Parse status
        status_code = 200
        if 'status' in response_data:
            try:
                status_code = int(response_data['status'].split()[0])
            except:
                pass
        
        # Parse headers
        headers = {}
        if 'headers' in response_data:
            for header in response_data['headers']:
                if len(header) >= 2:
                    headers[header[0]] = header[1]
        
        # Ensure content-type header
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'text/html'
        
        return {
            'statusCode': status_code,
            'headers': headers,
            'body': body.decode('utf-8') if body else ''
        }

# Create adapter
adapter = VercelWSGIAdapter(app)

# Vercel handler function
def handler(request):
    """Handle Vercel serverless function requests."""
    return adapter(request)

# For Vercel compatibility
def main(request):
    """Main entry point for Vercel."""
    return handler(request)

# Export for Vercel
__all__ = ['handler', 'main']
