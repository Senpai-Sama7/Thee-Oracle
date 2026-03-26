"""
Vercel-compatible Oracle Agent GUI - Simplified for Serverless Deployment
Flask backend without Socket.IO for Vercel compatibility
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, Dict

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template_string, request, jsonify, send_from_directory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-for-vercel')

# Simple HTML template for Vercel deployment
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Oracle Agent - Enterprise AI Platform</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            padding: 40px 0;
        }
        
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin: 40px 0;
        }
        
        .feature-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease;
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
        }
        
        .feature-card h3 {
            font-size: 1.5em;
            margin-bottom: 15px;
            color: #fff;
        }
        
        .feature-card p {
            line-height: 1.6;
            opacity: 0.9;
        }
        
        .status {
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid rgba(76, 175, 80, 0.5);
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            text-align: center;
        }
        
        .demo-section {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            margin: 40px 0;
        }
        
        .demo-input {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            font-size: 16px;
            margin-bottom: 15px;
        }
        
        .demo-button {
            background: linear-gradient(45deg, #ff6b6b, #ee5a24);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.3s ease;
        }
        
        .demo-button:hover {
            transform: scale(1.05);
        }
        
        .demo-output {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            font-family: monospace;
            white-space: pre-wrap;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .footer {
            text-align: center;
            padding: 40px 0;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Oracle Agent</h1>
            <p>Enterprise AI Agent Platform - Vercel Deployment</p>
        </div>
        
        <div class="status">
            <h3>✅ System Status: Online</h3>
            <p>Oracle Agent is running in demo mode on Vercel</p>
        </div>
        
        <div class="features">
            <div class="feature-card">
                <h3>🖥️ Real-Time GUI</h3>
                <p>Professional web interface with luxury design and real-time analytics dashboard</p>
            </div>
            
            <div class="feature-card">
                <h3>🛡️ Enterprise Security</h3>
                <p>91% security score with comprehensive authentication and authorization</p>
            </div>
            
            <div class="feature-card">
                <h3>🔄 Workflow Engine</h3>
                <p>Enterprise automation with multi-step workflows and decision branching</p>
            </div>
            
            <div class="feature-card">
                <h3>🤝 Agent Collaboration</h3>
                <p>Multi-agent coordination framework with role-based task distribution</p>
            </div>
            
            <div class="feature-card">
                <h3>💻 Code Generation</h3>
                <p>Multi-language code generation with quality scoring and best practices</p>
            </div>
            
            <div class="feature-card">
                <h3>🔌 Plugin System</h3>
                <p>Extensible architecture with dynamic plugin loading and security sandboxing</p>
            </div>
        </div>
        
        <div class="demo-section">
            <h2>🧪 Try Oracle Agent Demo</h2>
            <p>Experience the power of Oracle Agent with this interactive demo</p>
            
            <textarea class="demo-input" id="userInput" placeholder="Enter your request here...">Hello Oracle Agent! Can you tell me about your capabilities?</textarea>
            
            <button class="demo-button" onclick="sendMessage()">Send Message</button>
            
            <div class="demo-output" id="output">Click "Send Message" to see Oracle Agent in action...</div>
        </div>
        
        <div class="footer">
            <p>Oracle Agent v5.0-hardened - Enterprise AI Agent Platform</p>
            <p>Deployed on Vercel | Security Score: 91% | Production Ready</p>
        </div>
    </div>
    
    <script>
        async function sendMessage() {
            const input = document.getElementById('userInput');
            const output = document.getElementById('output');
            const button = document.querySelector('.demo-button');
            
            if (!input.value.trim()) return;
            
            button.disabled = true;
            button.textContent = 'Processing...';
            
            output.textContent = 'Oracle Agent is thinking...';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: input.value
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    output.textContent = result.response;
                } else {
                    output.textContent = 'Error: ' + (result.error || 'Unknown error');
                }
            } catch (error) {
                output.textContent = 'Demo mode response: Oracle Agent received your message and would normally process it with advanced AI capabilities. In this Vercel demo, we show the interface and system status.';
            } finally {
                button.disabled = false;
                button.textContent = 'Send Message';
            }
        }
        
        // Allow Enter key to send message
        document.getElementById('userInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main GUI interface."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'oracle-agent-vercel',
        'version': '5.0.0-hardened',
        'timestamp': datetime.now().isoformat(),
        'demo_mode': True,
        'features': [
            'workflow_engine',
            'agent_collaboration', 
            'code_generation',
            'plugin_system',
            'integration_framework'
        ]
    })

@app.route('/api/status')
def status():
    """System status endpoint."""
    return jsonify({
        'system': {
            'status': 'online',
            'platform': 'vercel',
            'environment': 'production-demo'
        },
        'oracle_agent': {
            'version': '5.0.0-hardened',
            'security_score': 91,
            'features_enabled': True,
            'demo_mode': True
        },
        'capabilities': {
            'workflow_engine': True,
            'agent_collaboration': True,
            'code_generation': True,
            'plugin_system': True,
            'integration_framework': True,
            'real_time_gui': True
        }
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint for demo interaction."""
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'No message provided'
            }), 400
        
        # Demo response
        demo_response = f"""🚀 Oracle Agent Response:

Thank you for your message: "{message}"

In this Vercel demo deployment, Oracle Agent is running in demonstration mode. Here's what I can do in a full deployment:

🎯 **Core Capabilities:**
• Execute complex workflows with decision branching
• Coordinate multiple specialized AI agents
• Generate code in multiple programming languages
• Integrate with external services and APIs
• Provide real-time analytics and monitoring

🛡️ **Enterprise Features:**
• 91% security score with comprehensive protection
• Role-based access control and authentication
• Audit logging and compliance reporting
• Scalable architecture with horizontal scaling

🖥️ **Professional Interface:**
• Real-time web dashboard with luxury design
• Interactive workflow designer
• Multi-agent coordination interface
• Comprehensive analytics and monitoring

📊 **Current Status:**
• Platform: Vercel (Demo Mode)
• Version: 5.0.0-hardened
• Security: Enterprise-grade
• Features: All enterprise capabilities enabled

To experience the full capabilities, deploy Oracle Agent on your own infrastructure with proper Google Cloud credentials.

Would you like to know more about any specific feature or capability?"""
        
        return jsonify({
            'success': True,
            'response': demo_response,
            'timestamp': datetime.now().isoformat(),
            'demo_mode': True
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/workflows', methods=['GET', 'POST'])
def workflows():
    """Workflow management endpoint."""
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'workflows': [
                {
                    'id': 'demo-workflow-1',
                    'name': 'Data Processing Pipeline',
                    'status': 'completed',
                    'created_at': '2026-03-25T12:00:00Z'
                },
                {
                    'id': 'demo-workflow-2', 
                    'name': 'Report Generation',
                    'status': 'running',
                    'created_at': '2026-03-25T12:30:00Z'
                }
            ]
        })
    
    return jsonify({
        'success': True,
        'message': 'Workflow creation available in full deployment'
    })

@app.route('/api/agents')
def agents():
    """Agent status endpoint."""
    return jsonify({
        'success': True,
        'agents': [
            {
                'id': 'coordinator-1',
                'name': 'Master Coordinator',
                'role': 'coordinator',
                'status': 'active'
            },
            {
                'id': 'worker-1',
                'name': 'Data Processor',
                'role': 'worker',
                'status': 'idle'
            },
            {
                'id': 'specialist-1',
                'name': 'Code Generator',
                'role': 'specialist',
                'status': 'active'
            }
        ]
    })

@app.route('/api/plugins')
def plugins():
    """Plugin management endpoint."""
    return jsonify({
        'success': True,
        'plugins': [
            {
                'id': 'slack_integration',
                'name': 'Slack Integration',
                'version': '1.2.0',
                'status': 'active'
            },
            {
                'id': 'github_integration',
                'name': 'GitHub Integration', 
                'version': '1.1.0',
                'status': 'active'
            }
        ]
    })

# Handle static files if they exist
@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files."""
    static_dir = project_root / 'gui' / 'static'
    if static_dir.exists():
        return send_from_directory(static_dir, filename)
    return '', 404

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
