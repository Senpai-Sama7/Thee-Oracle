"""
Oracle Agent GUI - Web Interface
Flask backend to serve the GUI and handle WebSocket communication
"""

import os
import sys
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

try:
    from flask_talisman import Talisman
except ImportError:
    class Talisman:  # type: ignore[no-redef]
        def __init__(self, app, **kwargs):
            logging.getLogger(__name__).warning("flask_talisman not installed; GUI security headers are disabled")


try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:
    def get_remote_address() -> str:
        return request.remote_addr or "127.0.0.1"

    class Limiter:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            logging.getLogger(__name__).warning("flask_limiter not installed; GUI rate limits are disabled")

        def limit(self, _limit: str):
            def decorator(func):
                return func

            return decorator

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oracle.agent_system import OracleAgent, OracleConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "oracle-gui-secret-key-change-in-production")

# Initialize security middleware
Talisman(
    app,
    force_https=app.config.get("FORCE_HTTPS", False),
    strict_transport_security=True,
    content_security_policy={
        "default-src": "'self'",
        "script-src": "'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com",
        "style-src": "'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
        "font-src": "'self' https://fonts.gstatic.com",
        "img-src": "'self' data: https:",
        "connect-src": "'self' ws: wss:",
    },
    referrer_policy="strict-origin-when-cross-origin",
    feature_policy={"geolocation": "'none'", "camera": "'none'", "microphone": "'none'"},
)

# Initialize rate limiting
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

# Initialize SocketIO for real-time communication (using threading mode for compatibility)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

@dataclass
class AppState:
    agent: Optional[OracleAgent] = None
    agent_config: Optional[OracleConfig] = None


app_state = AppState()


def initialize_agent() -> bool:
    """Initialize the Oracle Agent with current configuration."""
    try:
        # Load environment if .env exists
        if Path(".env").exists():
            with open(".env") as f:
                for line in f:
                    if line.strip() and not line.startswith("#") and "=" in line:
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value

        app_state.agent_config = OracleConfig()
        app_state.agent = OracleAgent(app_state.agent_config)
        logger.info("Oracle Agent initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Oracle Agent: {e}")
        return False


def require_auth(f):
    """Decorator to require authentication for API endpoints"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Simple API key authentication for demo
        # In production, use proper JWT or OAuth
        api_key = request.headers.get("X-API-Key")
        expected_key = os.environ.get("ORACLE_API_KEY", "demo-api-key")

        if not api_key or api_key != expected_key:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def index():
    """Main GUI interface."""
    return render_template("index.html")


@app.route("/api/status")
@limiter.limit("10 per minute")
def get_status():
    """Get agent status."""
    try:
        if not app_state.agent_config:
            return jsonify({"error": "No configuration loaded"}), 503

        status = {
            "initialized": app_state.agent is not None,
            "model_id": app_state.agent_config.model_id,
            "gcp_project": app_state.agent_config.gcp_project,
            "gcp_location": app_state.agent_config.gcp_location,
            "max_turns": app_state.agent_config.max_turns,
            "gcs_enabled": app_state.agent.gcs_backup_enabled if app_state.agent else False,
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/config", methods=["GET", "POST"])
@limiter.limit("5 per minute")
@require_auth
def handle_config():
    """Get or update configuration."""
    if request.method == "GET":
        try:
            if not app_state.agent_config:
                return jsonify({"error": "No configuration loaded"}), 503

            config = {
                "model_id": app_state.agent_config.model_id,
                "gcp_project": app_state.agent_config.gcp_project,
                "gcp_location": app_state.agent_config.gcp_location,
                "max_turns": app_state.agent_config.max_turns,
                "shell_timeout": app_state.agent_config.shell_timeout,
                "http_timeout": app_state.agent_config.http_timeout,
                "project_root": str(app_state.agent_config.project_root),
                "gcs_enabled": app_state.agent.gcs_backup_enabled if app_state.agent else False,
                "gcs_bucket": os.environ.get("GCS_BUCKET_NAME", ""),
                "log_level": os.environ.get("ORACLE_LOG_LEVEL", "INFO"),
            }

            return jsonify(config)
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return jsonify({"error": "Internal server error"}), 500

    # POST - update config (requires reinitialization)
    try:
        data = request.json

        # Validate data
        if not data:
            return jsonify({"success": False, "error": "No configuration data provided"}), 400

        # Update environment variables
        env_updates = {}

        if "model_id" in data and data["model_id"]:
            env_updates["ORACLE_MODEL_ID"] = data["model_id"]

        if "max_turns" in data and isinstance(data["max_turns"], int):
            env_updates["ORACLE_MAX_TURNS"] = str(data["max_turns"])

        if "shell_timeout" in data and isinstance(data["shell_timeout"], int):
            env_updates["ORACLE_SHELL_TIMEOUT"] = str(data["shell_timeout"])

        if "http_timeout" in data and isinstance(data["http_timeout"], int):
            env_updates["ORACLE_HTTP_TIMEOUT"] = str(data["http_timeout"])

        if "log_level" in data and data["log_level"]:
            env_updates["ORACLE_LOG_LEVEL"] = data["log_level"]

        if "gcs_bucket" in data and data["gcs_bucket"]:
            env_updates["GCS_BUCKET_NAME"] = data["gcs_bucket"]

        if "temperature" in data and isinstance(data["temperature"], (int, float)):
            env_updates["ORACLE_TEMPERATURE"] = str(data["temperature"])

        # Apply environment updates
        for key, value in env_updates.items():
            os.environ[key] = value
            # Also update .env file if it exists
            try:
                env_file = Path(".env")
                if env_file.exists():
                    content = env_file.read_text()
                    lines = content.split("\n")
                    updated_lines = []
                    key_found = False

                    for line in lines:
                        if line.strip() and not line.startswith("#") and "=" in line:
                            existing_key, existing_value = line.strip().split("=", 1)
                            if existing_key == key:
                                updated_lines.append(f"{key}={value}")
                                key_found = True
                            else:
                                updated_lines.append(line)
                        else:
                            updated_lines.append(line)

                    if not key_found:
                        updated_lines.append(f"{key}={value}")

                    env_file.write_text("\n".join(updated_lines))
            except Exception as e:
                logger.warning(f"Failed to update .env file: {e}")

        # Reinitialize agent with new configuration
        if initialize_agent():
            return jsonify(
                {
                    "success": True,
                    "message": "Configuration updated successfully",
                    "config": {
                        "model_id": app_state.agent_config.model_id,
                        "max_turns": app_state.agent_config.max_turns,
                        "shell_timeout": app_state.agent_config.shell_timeout,
                        "http_timeout": app_state.agent_config.http_timeout,
                        "gcs_enabled": app_state.agent.gcs_backup_enabled if app_state.agent else False,
                    },
                }
            )
        else:
            return jsonify({"success": False, "error": "Failed to reinitialize agent with new configuration"}), 500

    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/settings/export")
def export_settings():
    """Export current settings as JSON file."""
    try:
        if not app_state.agent_config:
            return jsonify({"error": "No configuration loaded"}), 400

        # Create export data
        export_data = {
            "oracle_agent_settings": {
                "exported_at": datetime.now().isoformat(),
                "version": "5.0.0",
                "settings": {
                    "model_id": app_state.agent_config.model_id,
                    "gcp_project": app_state.agent_config.gcp_project,
                    "gcp_location": app_state.agent_config.gcp_location,
                    "max_turns": app_state.agent_config.max_turns,
                    "shell_timeout": app_state.agent_config.shell_timeout,
                    "http_timeout": app_state.agent_config.http_timeout,
                    "project_root": str(app_state.agent_config.project_root),
                    "gcs_enabled": app_state.agent.gcs_backup_enabled if app_state.agent else False,
                    "gcs_bucket": os.environ.get("GCS_BUCKET_NAME", ""),
                    "log_level": os.environ.get("ORACLE_LOG_LEVEL", "INFO"),
                },
            }
        }

        return jsonify(export_data)

    except Exception as e:
        logger.error(f"Error exporting settings: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Get current settings."""
    try:
        if not app_state.agent_config:
            return jsonify({"error": "No configuration loaded"}), 400

        settings = {
            "model_id": app_state.agent_config.model_id,
            "gcp_project": app_state.agent_config.gcp_project,
            "gcp_location": app_state.agent_config.gcp_location,
            "max_turns": app_state.agent_config.max_turns,
            "shell_timeout": app_state.agent_config.shell_timeout,
            "http_timeout": app_state.agent_config.http_timeout,
            "project_root": str(app_state.agent_config.project_root),
            "gcs_enabled": app_state.agent.gcs_backup_enabled if app_state.agent else False,
            "gcs_bucket": os.environ.get("GCS_BUCKET_NAME", ""),
            "log_level": os.environ.get("ORACLE_LOG_LEVEL", "INFO"),
            "temperature": float(os.environ.get("ORACLE_TEMPERATURE", "0.7")),
        }

        return jsonify(settings)

    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "agent_initialized": app_state.agent is not None,
            "config_loaded": app_state.agent_config is not None,
            "gcs_enabled": app_state.agent.gcs_backup_enabled if app_state.agent else False,
            "version": "5.0.0",
        }

        # Add agent status if available
        if app_state.agent:
            health_status["agent_status"] = {
                "initialized": True,
                "model_id": app_state.agent_config.model_id if app_state.agent_config else None,
                "max_turns": app_state.agent_config.max_turns if app_state.agent_config else None,
            }

        return jsonify(health_status)

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return jsonify({"status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()}), 500


@app.route("/api/settings/reset", methods=["POST"])
def reset_settings():
    """Reset settings to defaults."""
    try:
        # Default settings
        defaults = {
            "ORACLE_MODEL_ID": "gemini-2.0-flash-exp",
            "ORACLE_MAX_TURNS": "20",
            "ORACLE_SHELL_TIMEOUT": "60",
            "ORACLE_HTTP_TIMEOUT": "15",
            "ORACLE_LOG_LEVEL": "INFO",
            "ORACLE_TEMPERATURE": "0.7",
        }

        # Apply defaults
        for key, value in defaults.items():
            os.environ[key] = value

        # Reinitialize agent
        if initialize_agent():
            return jsonify({"success": True, "message": "Settings reset to defaults"})
        else:
            return jsonify({"success": False, "error": "Failed to reinitialize agent"}), 500

    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/help/features")
def get_help_features():
    """Get help information about available features."""
    try:
        features = {
            "ai_conversations": {
                "title": "AI Conversations",
                "description": "Natural language conversations with Oracle Agent",
                "capabilities": [
                    "Answer questions and provide information",
                    "Execute commands and scripts",
                    "Manage files and directories",
                    "Make web requests and API calls",
                    "Analyze data and generate reports",
                ],
                "examples": [
                    "List the files in the current directory and tell me which ones are Python files",
                    "Create a backup of all .py files in a compressed archive",
                    "What's the weather like today?",
                ],
            },
            "tools": {
                "title": "Tool Execution",
                "description": "Direct access to system tools",
                "available_tools": [
                    {"name": "shell_execute", "description": "Run terminal commands", "example": "ls -la"},
                    {
                        "name": "file_system_ops",
                        "description": "Read, write, list, or delete files",
                        "operations": ["read", "write", "list", "delete"],
                    },
                    {
                        "name": "http_fetch",
                        "description": "Make HTTP requests to web APIs",
                        "example": "https://api.github.com/users",
                    },
                    {
                        "name": "vision_capture",
                        "description": "Capture screenshots for analysis",
                        "example": "Capture the screen and analyze the current state",
                    },
                ],
            },
            "settings": {
                "title": "Configuration Options",
                "categories": [
                    {"name": "AI Model", "options": ["model_id", "max_turns", "temperature"]},
                    {"name": "Security", "options": ["shell_timeout", "http_timeout", "file_sandbox"]},
                    {"name": "Cloud Storage", "options": ["gcs_backup", "gcs_bucket", "auto_backup"]},
                    {"name": "Advanced", "options": ["debug_mode", "metrics", "log_level"]},
                ],
            },
        }

        return jsonify(features)

    except Exception as e:
        logger.error(f"Error getting help features: {e}")
        return jsonify({"error": str(e)}), 500


@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")
    emit("connected", {"status": "connected", "timestamp": datetime.now().isoformat()})

    # Send current status
    if app_state.agent:
        emit(
            "agent_status",
            {
                "initialized": True,
                "model_id": app_state.agent.cfg.model_id,
                "gcs_enabled": app_state.agent.gcs_backup_enabled,
            },
        )
    else:
        emit("agent_status", {"initialized": False})


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on("send_message")
def handle_message(data):
    """Handle incoming chat message from client."""
    if not app_state.agent:
        emit("error", {"message": "Oracle Agent not initialized"})
        return

    try:
        prompt = data.get("message", "").strip()
        session_id = data.get("session_id", "default")

        if not prompt:
            emit("error", {"message": "Empty message"})
            return

        # Log the incoming message
        logger.info(f"[{session_id}] User: {prompt[:100]}")

        # Emit thinking indicator
        emit("thinking", {"session_id": session_id})

        # Process with Oracle Agent
        # Use run_async if available, otherwise fallback to sync
        try:
            # Try async version first
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            if hasattr(app_state.agent, "run_async"):
                response = loop.run_until_complete(app_state.agent.run_async(prompt, session_id))
            else:
                # Fallback to synchronous
                response = app_state.agent.run(prompt, session_id)

            loop.close()

        except Exception as e:
            logger.warning(f"Async execution failed, using sync: {e}")
            response = app_state.agent.run(prompt, session_id)

        # Emit the response
        emit(
            "message",
            {
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
            },
        )

        logger.info(f"[{session_id}] Assistant: {response[:100]}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        emit("error", {"message": str(e)})


@socketio.on("execute_tool")
def handle_tool_execution(data):
    """Handle direct tool execution from GUI."""
    if not app_state.agent:
        emit("error", {"message": "Agent not initialized"})
        return

    try:
        tool_name = data.get("tool")
        args = data.get("args", {})

        emit("tool_executing", {"tool": tool_name, "args": args})

        # Execute tool via agent's tool executor
        if hasattr(app_state.agent, "_tool_registry") and app_state.agent._tool_registry:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(app_state.agent._tool_registry.dispatch(tool_name, args))
            loop.close()
        else:
            result = app_state.agent._dispatch(tool_name, args)

        emit("tool_result", {"tool": tool_name, "result": result, "timestamp": datetime.now().isoformat()})

    except Exception as e:
        emit("error", {"message": f"Tool execution failed: {str(e)}"})


@socketio.on("backup_to_gcs")
def handle_backup():
    """Trigger GCS backup."""
    if not app_state.agent:
        emit("error", {"message": "Agent not initialized"})
        return

    try:
        result = app_state.agent.backup_to_gcs()
        emit("backup_result", result)
    except Exception as e:
        emit("error", {"message": f"Backup failed: {str(e)}"})


@socketio.on("clear_history")
def clear_history(data):
    """Clear conversation history for a session."""
    session_id = data.get("session_id", "default")

    if app_state.agent and hasattr(app_state.agent, "db"):
        try:
            # Save empty history to clear
            app_state.agent.db.save_history(session_id, [])
            emit("history_cleared", {"session_id": session_id})
        except Exception as e:
            emit("error", {"message": f"Failed to clear history: {str(e)}"})


@app.route("/static/<path:filename>")
def serve_static(filename):
    """Serve static files."""
    return send_from_directory("static", filename)


def create_gui_directories():
    """Create necessary directories for GUI."""
    gui_dir = Path(__file__).parent
    templates_dir = gui_dir / "templates"
    static_dir = gui_dir / "static"
    css_dir = static_dir / "css"
    js_dir = static_dir / "js"

    for dir_path in [templates_dir, static_dir, css_dir, js_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)

    return templates_dir, static_dir


if __name__ == "__main__":
    # Create directories
    templates_dir, static_dir = create_gui_directories()

    # Initialize agent
    logger.info("Initializing Oracle Agent...")
    if initialize_agent():
        logger.info("Agent ready!")
    else:
        logger.warning("Agent initialization failed - GUI will show error state")

    # Run the Flask-SocketIO server
    logger.info("Starting Oracle GUI on http://localhost:5001")
    socketio.run(app, host="0.0.0.0", port=5001, debug=False)
