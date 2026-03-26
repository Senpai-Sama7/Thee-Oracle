"""Oracle Agent - Flask app for Vercel."""

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    """Main page."""
    return """<!DOCTYPE html>
<html>
<head><title>Oracle Agent</title></head>
<body style="font-family:Arial;text-align:center;padding:50px;background:linear-gradient(135deg,#667eea,#764ba2);color:white">
    <h1>🚀 Oracle Agent</h1>
    <h2 style="color:#4CAF50">✅ Working!</h2>
    <p>Vercel deployment successful</p>
</body>
</html>"""

@app.route('/api/health')
def health():
    """Health check."""
    return jsonify({"status": "healthy", "service": "oracle-agent"})

@app.route('/api/status')
def status():
    """System status."""
    return jsonify({"status": "online", "version": "5.0.0"})

# WSGI handler for Vercel
def handler(environ, start_response):
    """WSGI entry point."""
    return app(environ, start_response)
