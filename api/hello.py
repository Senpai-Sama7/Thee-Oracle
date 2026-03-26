"""Simple Vercel serverless function for testing."""

def handler(request):
    """Simple handler function."""
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': '{"message": "Hello from Vercel!"}'
    }
