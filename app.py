"""Oracle Agent - Flask app for Vercel deployment."""

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    """Main page."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Oracle Agent - Vercel</title>
    <style>
        body { font-family: Arial; text-align: center; padding: 50px; 
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
               color: white; min-height: 100vh; margin: 0; }
        .container { max-width: 800px; margin: 0 auto; background: rgba(255,255,255,0.1);
                     backdrop-filter: blur(10px); border-radius: 20px; padding: 40px; }
        h1 { font-size: 3em; }
        .success { color: #4CAF50; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Oracle Agent</h1>
        <h2 class="success">✅ Vercel Deployment Working!</h2>
        <p>Your Oracle Agent is successfully deployed and running.</p>
    </div>
</body>
</html>
    """

@app.route('/api/health')
def health():
    """Health check."""
    return jsonify({"status": "healthy", "service": "oracle-agent"})

@app.route('/api/status')
def status():
    """System status."""
    return jsonify({
        "status": "online",
        "version": "5.0.0-hardened",
        "features": ["workflow_engine", "agent_collaboration", "code_generation"]
    })

if __name__ == '__main__':
    app.run(debug=True)
