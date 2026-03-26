"""API test endpoint for Oracle Agent on Vercel."""

import json

def handler(event=None, context=None):
    """API test endpoint."""
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
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
            'deployment': 'vercel-serverless'
        })
    }

# Export for Vercel
__all__ = ['handler']
