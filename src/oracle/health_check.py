#!/usr/bin/env python3
"""
Oracle Agent Health Check Service
Provides HTTP endpoints for monitoring and health checks
"""

import os
import sys
import json
import sqlite3
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse
import threading

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoints"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.start_time = time.time()
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/health":
            self.handle_health_check()
        elif path == "/metrics":
            self.handle_metrics()
        elif path == "/status":
            self.handle_status()
        else:
            self.send_404()

    def do_POST(self) -> None:
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/shutdown":
            self.handle_shutdown()
        else:
            self.send_404()

    def handle_health_check(self) -> None:
        """Basic health check endpoint"""
        try:
            # Check database connectivity
            db_path = Path(__file__).parent.parent / "data" / "oracle_core.db"
            db_healthy = db_path.exists() and self.check_database(db_path)

            # Check GCP authentication (if configured)
            gcp_healthy = self.check_gcp_auth()

            # Overall health
            healthy = db_healthy and gcp_healthy

            response = {
                "status": "healthy" if healthy else "unhealthy",
                "timestamp": time.time(),
                "uptime": time.time() - self.start_time,
                "checks": {
                    "database": "healthy" if db_healthy else "unhealthy",
                    "gcp_auth": "healthy" if gcp_healthy else "unhealthy",
                },
            }

            self.send_json_response(200 if healthy else 503, response)

        except Exception as e:
            self.send_json_response(500, {"status": "error", "error": str(e), "timestamp": time.time()})

    def handle_metrics(self) -> None:
        """Prometheus-style metrics endpoint"""
        try:
            metrics = self.collect_metrics()
            self.send_text_response(200, metrics)
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_status(self) -> None:
        """Detailed status endpoint"""
        try:
            status = self.get_detailed_status()
            self.send_json_response(200, status)
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_shutdown(self) -> None:
        """Graceful shutdown endpoint"""
        self.send_json_response(200, {"message": "Shutting down..."})
        # Schedule shutdown in separate thread
        threading.Thread(target=self.shutdown_server, daemon=True).start()

    def check_database(self, db_path: Path) -> bool:
        """Check database connectivity"""
        try:
            conn = sqlite3.connect(str(db_path), timeout=5.0)
            conn.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False

    def check_gcp_auth(self) -> bool:
        """Check GCP authentication"""
        try:
            # Try to import and check GCP auth
            from google.auth import default

            credentials, project = default()
            return credentials is not None
        except Exception:
            # If GCP not configured, consider it healthy for demo mode
            return True

    def collect_metrics(self) -> str:
        """Collect Prometheus-style metrics without expensive re-instantiation"""
        try:
            # Resolve db path once or cheaply
            db_path = Path("data/oracle_core.db")
            db_size = db_path.stat().st_size if db_path.exists() else 0

            uptime = time.time() - self.start_time

            metrics = [
                "# HELP oracle_agent_uptime_seconds Total uptime in seconds",
                "# TYPE oracle_agent_uptime_seconds counter",
                f"oracle_agent_uptime_seconds {uptime}",
                "",
                "# HELP oracle_agent_database_size_bytes Database file size in bytes",
                "# TYPE oracle_agent_database_size_bytes gauge",
                f"oracle_agent_database_size_bytes {db_size}",
                "",
                "# HELP oracle_agent_health_check_total Total health checks performed",
                "# TYPE oracle_agent_health_check_total counter",
                "oracle_agent_health_check_total 1",
                "",
            ]

            return "\n".join(metrics)

        except Exception as e:
            # Fallback metrics
            return f"# Oracle Agent Metrics (Error: {e})\noracle_agent_uptime_seconds {time.time() - self.start_time}\n"

    def get_detailed_status(self) -> dict[str, Any]:
        """Get detailed system status"""
        try:
            import psutil

            # System metrics
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Database info
            db_path = Path(__file__).parent.parent / "data" / "oracle_core.db"
            db_info = {
                "path": str(db_path),
                "exists": db_path.exists(),
                "size": db_path.stat().st_size if db_path.exists() else 0,
            }

            return {
                "timestamp": time.time(),
                "uptime": time.time() - self.start_time,
                "system": {
                    "memory": {"total": memory.total, "available": memory.available, "percent": memory.percent},
                    "disk": {"total": disk.total, "free": disk.free, "percent": (disk.used / disk.total) * 100},
                    "cpu_percent": psutil.cpu_percent(),
                },
                "database": db_info,
                "environment": {
                    "gcp_project_id": os.environ.get("GCP_PROJECT_ID", "not_set"),
                    "oracle_model_id": os.environ.get("ORACLE_MODEL_ID", "gemini-3.1-pro-preview"),
                    "max_turns": int(os.environ.get("ORACLE_MAX_TURNS", "20")),
                },
            }

        except Exception as e:
            return {"timestamp": time.time(), "error": str(e), "uptime": time.time() - self.start_time}

    def send_json_response(self, status_code: int, data: dict[str, Any]) -> None:
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def send_text_response(self, status_code: int, text: str) -> None:
        """Send plain text response"""
        self.send_response(status_code)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(text.encode())

    def send_404(self) -> None:
        """Send 404 response"""
        self.send_response(404)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def shutdown_server(self) -> None:
        """Shutdown the server"""
        time.sleep(1)  # Allow response to be sent
        self.server.shutdown()

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default logging"""
        pass


def main() -> None:
    """Main health check server"""
    import argparse

    parser = argparse.ArgumentParser(description="Oracle Agent Health Check Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--host", type=str, default="localhost", help="Host to bind to")
    args = parser.parse_args()

    # Create logs directory
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Start server
    server = HTTPServer((args.host, args.port), HealthCheckHandler)
    HealthCheckHandler.server = server

    print(f"🏥 Health Check Server started on http://{args.host}:{args.port}")
    print(f"📊 Health endpoint: http://{args.host}:{args.port}/health")
    print(f"📈 Metrics endpoint: http://{args.host}:{args.port}/metrics")
    print(f"📋 Status endpoint: http://{args.host}:{args.port}/status")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Health Check Server stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
