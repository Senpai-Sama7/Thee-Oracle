"""
Oracle Agent GUI - Web Interface
Flask backend to serve the GUI and handle WebSocket communication
"""

import os
import re
import sys
import asyncio
import logging
import secrets
from collections import defaultdict
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
from threading import Lock
from time import monotonic

from flask import Flask, render_template, request, jsonify, send_from_directory, session
from flask_socketio import SocketIO, emit

try:
    from flask_talisman import Talisman
except ImportError:
    class Talisman:  # type: ignore[no-redef]
        def __init__(self, app, **kwargs):
            del app, kwargs
            logging.getLogger(__name__).debug("Using built-in GUI security header fallback")


try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:
    def get_remote_address() -> str:
        return request.remote_addr or "127.0.0.1"

    class Limiter:  # type: ignore[no-redef]
        _window_seconds = {"minute": 60, "hour": 3600, "day": 86400}

        def __init__(self, *args, **kwargs):
            logging.getLogger(__name__).debug("Using in-process fallback rate limiting")
            self._calls: dict[str, list[float]] = defaultdict(list)
            self._key_func = kwargs.get("key_func", get_remote_address)
            self._lock = Lock()

        @classmethod
        def _parse_limit(cls, raw_limit: str) -> tuple[int, int]:
            parts = raw_limit.strip().split()
            if len(parts) != 3 or parts[1] != "per":
                raise ValueError(f"Unsupported limit format: {raw_limit}")
            count = int(parts[0])
            unit = parts[2].rstrip("s").lower()
            if unit not in cls._window_seconds:
                raise ValueError(f"Unsupported limit unit: {unit}")
            return count, cls._window_seconds[unit]

        def limit(self, raw_limit: str):
            max_calls, window_seconds = self._parse_limit(raw_limit)

            def decorator(func):
                @wraps(func)
                def wrapped(*args, **kwargs):
                    key = f"{func.__name__}:{self._key_func()}"
                    now = monotonic()
                    with self._lock:
                        calls = [stamp for stamp in self._calls[key] if now - stamp < window_seconds]
                        if len(calls) >= max_calls:
                            return jsonify({"error": "Rate limit exceeded"}), 429
                        calls.append(now)
                        self._calls[key] = calls
                    return func(*args, **kwargs)

                return wrapped

            return decorator

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oracle.agent_system import OracleAgent, OracleConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GUI_ALLOWED_DIRECT_TOOLS = frozenset(
    {
        "shell_execute",
        "file_system_ops",
        "http_fetch",
        "vision_capture",
    }
)
MAX_GUI_MESSAGE_LENGTH = 8_000
MAX_GUI_SESSION_ID_LENGTH = 128


def env_flag(*names: str) -> bool:
    for name in names:
        if os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}:
            return True
    return False


GUI_SECURITY_POLICY = {
    "default-src": "'self'",
    "script-src": "'self' https://cdnjs.cloudflare.com https://fonts.googleapis.com",
    "style-src": "'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
    "font-src": "'self' https://fonts.gstatic.com",
    "img-src": "'self' data: https:",
    "connect-src": "'self' ws: wss:",
    "object-src": "'none'",
    "base-uri": "'self'",
}

# Initialize Flask app
app = Flask(__name__, template_folder="templates", static_folder="static")
configured_gui_host = os.environ.get("ORACLE_GUI_HOST", "127.0.0.1").strip() or "127.0.0.1"
secret_key = os.environ.get("SECRET_KEY", "").strip()
if not secret_key:
    secret_key = secrets.token_urlsafe(32)
    if configured_gui_host in {"127.0.0.1", "localhost", "::1"}:
        logger.debug("SECRET_KEY not set; using ephemeral GUI secret key for local development")
    else:
        logger.warning("SECRET_KEY not set for a non-loopback GUI bind; using ephemeral GUI secret key")
force_https = env_flag("ORACLE_GUI_FORCE_HTTPS", "FORCE_HTTPS")
app.config["SECRET_KEY"] = secret_key
app.config["FORCE_HTTPS"] = force_https
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = force_https

# Initialize security middleware
Talisman(
    app,
    force_https=app.config["FORCE_HTTPS"],
    strict_transport_security=True,
    content_security_policy=GUI_SECURITY_POLICY,
    referrer_policy="strict-origin-when-cross-origin",
    feature_policy={"geolocation": "'none'", "camera": "'none'", "microphone": "'none'"},
)

# Initialize rate limiting
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])


def get_socket_cors_origins() -> str | list[str] | None:
    raw_origins = os.environ.get("ORACLE_GUI_CORS_ORIGINS", "").strip()
    if not raw_origins:
        return None
    if raw_origins == "*" and env_flag("ORACLE_GUI_ALLOW_ANY_ORIGIN"):
        return "*"
    if raw_origins == "*":
        logger.warning("Ignoring wildcard ORACLE_GUI_CORS_ORIGINS without ORACLE_GUI_ALLOW_ANY_ORIGIN=true")
        return None
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


# Initialize SocketIO for real-time communication (using threading mode for compatibility)
socketio = SocketIO(app, cors_allowed_origins=get_socket_cors_origins(), async_mode="threading")

@dataclass
class AppState:
    agent: Optional[OracleAgent] = None
    agent_config: Optional[OracleConfig] = None


app_state = AppState()


def is_vercel_deployment() -> bool:
    return env_flag("VERCEL") or bool(os.environ.get("VERCEL_URL", "").strip())


def realtime_transport_enabled() -> bool:
    if env_flag("ORACLE_GUI_FORCE_HTTP", "ORACLE_GUI_DISABLE_SOCKETIO"):
        return False
    return not is_vercel_deployment()


def current_transport_status() -> dict[str, Any]:
    return {
        "mode": "socketio" if realtime_transport_enabled() else "http-fallback",
        "realtime_enabled": realtime_transport_enabled(),
        "platform": "vercel" if is_vercel_deployment() else "self-hosted",
    }


def get_expected_api_key() -> str:
    return os.environ.get("ORACLE_API_KEY", "").strip()


def is_authorized_api_key(api_key: str | None) -> bool:
    expected_key = get_expected_api_key()
    if not expected_key:
        return False
    if not api_key:
        return False
    return secrets.compare_digest(api_key, expected_key)


def serialize_csp(policy: dict[str, str]) -> str:
    return "; ".join(f"{directive} {value}" for directive, value in policy.items())


def normalize_session_id(raw_value: Any) -> str:
    if not isinstance(raw_value, str):
        return "default"
    cleaned = re.sub(r"[\x00-\x1f\x7f]+", " ", raw_value).strip()
    if not cleaned:
        return "default"
    return cleaned[:MAX_GUI_SESSION_ID_LENGTH]


def run_agent_prompt(prompt: str, session_id: str) -> str:
    if not app_state.agent:
        raise RuntimeError("Oracle Agent not initialized")

    loop: asyncio.AbstractEventLoop | None = None
    if hasattr(app_state.agent, "run_async"):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(app_state.agent.run_async(prompt, session_id))
        except Exception as exc:
            logger.warning("Async execution failed, using sync: %s", exc)
        finally:
            if loop is not None:
                loop.close()
            asyncio.set_event_loop(None)

    return app_state.agent.run(prompt, session_id)


def execute_gui_tool(tool_name: str, args: dict[str, Any]) -> Any:
    if not app_state.agent:
        raise RuntimeError("Oracle Agent not initialized")

    if hasattr(app_state.agent, "_tool_registry") and app_state.agent._tool_registry:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(app_state.agent._tool_registry.dispatch(tool_name, args))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    return app_state.agent._dispatch(tool_name, args)


def clear_session_history(session_id: str) -> None:
    if not app_state.agent or not hasattr(app_state.agent, "db"):
        raise RuntimeError("Oracle Agent not initialized")
    app_state.agent.db.save_history(session_id, [])


def socket_request_authorized() -> bool:
    expected_key = get_expected_api_key()
    if not expected_key:
        return True
    return bool(session.get("socket_authenticated"))


@app.after_request
def apply_security_headers(response):
    response.headers.setdefault("Content-Security-Policy", serialize_csp(GUI_SECURITY_POLICY))
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    return response


def initialize_agent() -> bool:
    """Initialize the Oracle Agent with current configuration."""
    try:
        # Load environment if .env exists
        if Path(".env").exists():
            with open(".env") as f:
                for line in f:
                    if line.strip() and not line.startswith("#") and "=" in line:
                        key, value = line.strip().split("=", 1)
                        cleaned = value.strip()
                        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
                            cleaned = cleaned[1:-1].strip()
                        os.environ[key] = cleaned

        app_state.agent_config = OracleConfig()
        app_state.agent = OracleAgent(app_state.agent_config)
        logger.info("Oracle Agent initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Oracle Agent: {e}")
        return False


def get_skill_catalog() -> list[dict[str, Any]]:
    """Get the current skill catalog from the active agent."""
    if not app_state.agent or not hasattr(app_state.agent, "get_skill_catalog"):
        return []
    try:
        return app_state.agent.get_skill_catalog()
    except Exception as exc:
        logger.warning("Unable to read skill catalog: %s", exc)
        return []


def emit_gui_error(message: str) -> None:
    payload = {"message": message}
    emit("agent_error", payload)


def sanitize_skill_catalog(catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a UI-safe view of the skill catalog without local filesystem paths."""
    sanitized: list[dict[str, Any]] = []
    for entry in catalog:
        resources = entry.get("resources", {})
        scripts = resources.get("scripts", []) if isinstance(resources, dict) else []
        references = resources.get("references", []) if isinstance(resources, dict) else []
        assets = resources.get("assets", []) if isinstance(resources, dict) else []
        tool_names = entry.get("tool_names", [])
        triggers = entry.get("triggers", [])
        allowed_tools = entry.get("allowed_tools", [])

        sanitized.append(
            {
                "name": entry.get("name", "unknown-skill"),
                "description": entry.get("description", ""),
                "source_type": entry.get("source_type", "unknown"),
                "tool_names": tool_names if isinstance(tool_names, list) else [],
                "triggers": triggers if isinstance(triggers, list) else [],
                "allowed_tools": allowed_tools if isinstance(allowed_tools, list) else [],
                "resources": {
                    "scripts": scripts if isinstance(scripts, list) else [],
                    "references": references if isinstance(references, list) else [],
                    "assets": assets if isinstance(assets, list) else [],
                },
                "resource_counts": {
                    "scripts": len(scripts) if isinstance(scripts, list) else 0,
                    "references": len(references) if isinstance(references, list) else 0,
                    "assets": len(assets) if isinstance(assets, list) else 0,
                },
            }
        )
    return sanitized


def require_auth(f):
    """Decorator to require authentication for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        expected_key = get_expected_api_key()
        if not expected_key:
            return f(*args, **kwargs)

        api_key = request.headers.get("X-API-Key")
        if not is_authorized_api_key(api_key):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def index():
    """Main GUI interface."""
    transport = current_transport_status()
    return render_template(
        "index.html",
        realtime_enabled=transport["realtime_enabled"],
        transport_mode=transport["mode"],
    )


@app.route("/api/status")
@limiter.limit("10 per minute")
def get_status():
    """Get agent status."""
    try:
        if not app_state.agent_config:
            return jsonify({"error": "No configuration loaded"}), 503

        skill_catalog = sanitize_skill_catalog(get_skill_catalog())

        status = {
            "initialized": app_state.agent is not None,
            "model_id": app_state.agent_config.model_id,
            "gcp_project": app_state.agent_config.gcp_project,
            "gcp_location": app_state.agent_config.gcp_location,
            "max_turns": app_state.agent_config.max_turns,
            "gcs_enabled": app_state.agent.gcs_backup_enabled if app_state.agent else False,
            "skill_count": len(skill_catalog),
            "skill_tool_count": sum(len(entry["tool_names"]) for entry in skill_catalog),
            "skill_names": [entry["name"] for entry in skill_catalog[:6]],
            "transport": current_transport_status(),
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/chat", methods=["POST"])
@limiter.limit("20 per minute")
@require_auth
def chat_via_http():
    """HTTP fallback chat endpoint for serverless environments."""
    if not app_state.agent:
        return jsonify({"error": "Oracle Agent not initialized"}), 503

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid message payload"}), 400

    prompt = data.get("message", "")
    session_id = normalize_session_id(data.get("session_id", "default"))

    if not isinstance(prompt, str):
        return jsonify({"error": "Message must be a string"}), 400
    prompt = prompt.strip()

    if not prompt:
        return jsonify({"error": "Empty message"}), 400
    if len(prompt) > MAX_GUI_MESSAGE_LENGTH:
        return jsonify({"error": "Message exceeds GUI limit"}), 400

    try:
        logger.info("[%s] User: %s", session_id, prompt[:100])
        response = run_agent_prompt(prompt, session_id)
        logger.info("[%s] Assistant: %s", session_id, response[:100])
        return jsonify(
            {
                "session_id": session_id,
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "transport": current_transport_status(),
            }
        )
    except Exception as exc:
        logger.error("Error processing HTTP chat message: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/skills", methods=["GET"])
@limiter.limit("20 per minute")
def get_skills():
    """Return the sanitized discovered skill catalog for the GUI."""
    try:
        catalog = sanitize_skill_catalog(get_skill_catalog())
        return jsonify(
            {
                "skills": catalog,
                "count": len(catalog),
                "tool_count": sum(len(entry["tool_names"]) for entry in catalog),
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as exc:
        logger.error("Error getting skill catalog: %s", exc)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/skills/reload", methods=["POST"])
@limiter.limit("5 per minute")
@require_auth
def reload_skills():
    """Reload local skills without rebuilding the entire GUI runtime."""
    if not app_state.agent or not hasattr(app_state.agent, "reload_skills"):
        return jsonify({"success": False, "error": "Skill runtime is unavailable"}), 503

    try:
        app_state.agent.reload_skills()
        catalog = sanitize_skill_catalog(get_skill_catalog())
        return jsonify(
            {
                "success": True,
                "message": "Skills reloaded successfully",
                "count": len(catalog),
                "tool_count": sum(len(entry["tool_names"]) for entry in catalog),
                "skills": catalog,
            }
        )
    except Exception as exc:
        logger.error("Error reloading skills: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/tools/execute", methods=["POST"])
@limiter.limit("10 per minute")
@require_auth
def execute_tool_http():
    """HTTP fallback direct-tool endpoint for serverless environments."""
    if not app_state.agent:
        return jsonify({"error": "Agent not initialized"}), 503

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid tool payload"}), 400

    tool_name = data.get("tool")
    args = data.get("args", {})

    if not isinstance(tool_name, str) or tool_name not in GUI_ALLOWED_DIRECT_TOOLS:
        return jsonify({"error": "Unsupported tool"}), 400
    if not isinstance(args, dict):
        return jsonify({"error": "Tool arguments must be an object"}), 400

    try:
        result = execute_gui_tool(tool_name, args)
        return jsonify({"tool": tool_name, "result": result, "timestamp": datetime.now().isoformat()})
    except Exception as exc:
        logger.error("Error executing HTTP tool %s: %s", tool_name, exc)
        return jsonify({"error": f"Tool execution failed: {exc}"}), 500


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
@require_auth
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
@require_auth
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
        skill_catalog = sanitize_skill_catalog(get_skill_catalog())
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "agent_initialized": app_state.agent is not None,
            "config_loaded": app_state.agent_config is not None,
            "gcs_enabled": app_state.agent.gcs_backup_enabled if app_state.agent else False,
            "skill_count": len(skill_catalog),
            "transport": current_transport_status(),
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


@app.route("/api/backup", methods=["POST"])
@limiter.limit("5 per minute")
@require_auth
def backup_via_http():
    """HTTP fallback backup endpoint for serverless environments."""
    if not app_state.agent:
        return jsonify({"error": "Agent not initialized"}), 503

    try:
        result = app_state.agent.backup_to_gcs()
        return jsonify(result)
    except Exception as exc:
        logger.error("Backup failed: %s", exc)
        return jsonify({"error": f"Backup failed: {exc}"}), 500


@app.route("/api/history/clear", methods=["POST"])
@limiter.limit("10 per minute")
@require_auth
def clear_history_via_http():
    """HTTP fallback clear-history endpoint for serverless environments."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid clear-history payload"}), 400

    session_id = normalize_session_id(data.get("session_id", "default"))

    try:
        clear_session_history(session_id)
        return jsonify({"session_id": session_id, "cleared": True, "timestamp": datetime.now().isoformat()})
    except Exception as exc:
        logger.error("Failed to clear history: %s", exc)
        return jsonify({"error": f"Failed to clear history: {exc}"}), 500


@app.route("/api/settings/reset", methods=["POST"])
@require_auth
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
        skill_catalog = sanitize_skill_catalog(get_skill_catalog())
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

        if skill_catalog:
            features["skills"] = {
                "title": "Skill Fabric",
                "description": (
                    "Repository-local operating procedures loaded from "
                    "Claude-style SKILL.md packages and legacy Python skills."
                ),
                "capabilities": [
                    f"{len(skill_catalog)} skills are currently discovered in the local workspace.",
                    "Prompt-time skill selection injects the most relevant operating instructions automatically.",
                    "Instruction-only skills and tool-backed skills can coexist in the same catalog.",
                ],
                "examples": [entry["name"] for entry in skill_catalog[:6]],
            }

        return jsonify(features)

    except Exception as e:
        logger.error(f"Error getting help features: {e}")
        return jsonify({"error": str(e)}), 500


@socketio.on("connect")
def handle_connect(auth: Optional[dict[str, Any]] = None):
    """Handle client connection."""
    expected_key = get_expected_api_key()
    if expected_key:
        provided_key = auth.get("apiKey") if isinstance(auth, dict) else None
        if not is_authorized_api_key(provided_key):
            logger.warning("Rejected unauthorized GUI socket connection: sid=%s", request.sid)
            return False
        session["socket_authenticated"] = True

    logger.info(f"Client connected: {request.sid}")
    emit("connected", {"status": "connected", "timestamp": datetime.now().isoformat()})

    # Send current status
    if app_state.agent:
        skill_catalog = sanitize_skill_catalog(get_skill_catalog())
        emit(
            "agent_status",
            {
                "initialized": True,
                "model_id": app_state.agent.cfg.model_id,
                "gcs_enabled": app_state.agent.gcs_backup_enabled,
                "skill_count": len(skill_catalog),
            },
        )
    else:
        emit("agent_status", {"initialized": False})


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    session.pop("socket_authenticated", None)
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on("send_message")
def handle_message(data):
    """Handle incoming chat message from client."""
    if not socket_request_authorized():
        emit_gui_error("Unauthorized")
        return

    if not app_state.agent:
        emit_gui_error("Oracle Agent not initialized")
        return

    try:
        if not isinstance(data, dict):
            emit_gui_error("Invalid message payload")
            return

        prompt = data.get("message", "")
        session_id = normalize_session_id(data.get("session_id", "default"))

        if not isinstance(prompt, str):
            emit_gui_error("Message must be a string")
            return
        prompt = prompt.strip()

        if not prompt:
            emit_gui_error("Empty message")
            return
        if len(prompt) > MAX_GUI_MESSAGE_LENGTH:
            emit_gui_error("Message exceeds GUI limit")
            return

        # Log the incoming message
        logger.info(f"[{session_id}] User: {prompt[:100]}")

        # Emit thinking indicator
        emit("thinking", {"session_id": session_id})

        response = run_agent_prompt(prompt, session_id)

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
        emit_gui_error(str(e))


@socketio.on("execute_tool")
def handle_tool_execution(data):
    """Handle direct tool execution from GUI."""
    if not socket_request_authorized():
        emit_gui_error("Unauthorized")
        return

    if not app_state.agent:
        emit_gui_error("Agent not initialized")
        return

    try:
        if not isinstance(data, dict):
            emit_gui_error("Invalid tool payload")
            return

        tool_name = data.get("tool")
        args = data.get("args", {})

        if not isinstance(tool_name, str) or tool_name not in GUI_ALLOWED_DIRECT_TOOLS:
            emit_gui_error("Unsupported tool")
            return
        if not isinstance(args, dict):
            emit_gui_error("Tool arguments must be an object")
            return

        emit("tool_executing", {"tool": tool_name, "args": args})

        # Execute tool via agent's tool executor
        result = execute_gui_tool(tool_name, args)

        emit("tool_result", {"tool": tool_name, "result": result, "timestamp": datetime.now().isoformat()})

    except Exception as e:
        emit_gui_error(f"Tool execution failed: {str(e)}")


@socketio.on("backup_to_gcs")
def handle_backup():
    """Trigger GCS backup."""
    if not socket_request_authorized():
        emit_gui_error("Unauthorized")
        return

    if not app_state.agent:
        emit_gui_error("Agent not initialized")
        return

    try:
        result = app_state.agent.backup_to_gcs()
        emit("backup_result", result)
    except Exception as e:
        emit_gui_error(f"Backup failed: {str(e)}")


@socketio.on("clear_history")
def clear_history(data):
    """Clear conversation history for a session."""
    if not socket_request_authorized():
        emit_gui_error("Unauthorized")
        return

    if not isinstance(data, dict):
        emit_gui_error("Invalid clear-history payload")
        return

    session_id = normalize_session_id(data.get("session_id", "default"))

    if app_state.agent and hasattr(app_state.agent, "db"):
        try:
            clear_session_history(session_id)
            emit("history_cleared", {"session_id": session_id})
        except Exception as e:
            emit_gui_error(f"Failed to clear history: {str(e)}")


@app.route("/favicon.ico")
def favicon():
    """Serve the GUI favicon to avoid browser 404 noise."""
    return send_from_directory(app.static_folder, "favicon.svg", mimetype="image/svg+xml")


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
    gui_host = os.environ.get("ORACLE_GUI_HOST", "127.0.0.1").strip() or "127.0.0.1"
    gui_port = int(os.environ.get("ORACLE_GUI_PORT", "5001"))

    # Create directories
    templates_dir, static_dir = create_gui_directories()

    # Initialize agent
    logger.info("Initializing Oracle Agent...")
    if initialize_agent():
        logger.info("Agent ready!")
    else:
        logger.warning("Agent initialization failed - GUI will show error state")

    # Run the Flask-SocketIO server
    logger.info("Starting Oracle GUI on http://%s:%s", gui_host, gui_port)
    socketio.run(app, host=gui_host, port=gui_port, debug=False)
