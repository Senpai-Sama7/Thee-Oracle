#!/usr/bin/env python3
"""
Oracle Agent Production Entry Point
Enhanced with health check service and production features
"""

import sys
import os
import signal
import time
import threading
from pathlib import Path
from typing import Any

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def start_health_check() -> None:
    """Start health check server in background"""
    try:
        from oracle.health_check import main as health_main
        import sys

        # Store original sys.argv
        original_argv = sys.argv

        # Set up arguments for health check
        sys.argv = ["health_check.py", "--port", "8080"]

        # Run health check in background thread
        health_thread = threading.Thread(target=health_main, daemon=True)
        health_thread.start()
        time.sleep(2)  # Let health check server start

        # Restore original sys.argv
        sys.argv = original_argv
        print("🏥 Health check server started on port 8080")
    except Exception as e:
        print(f"⚠️  Health check server failed to start: {e}")


def main() -> int:
    """Optimized Oracle Agent entry point for production deployment"""
    print("🚀 Oracle Agent Production System")
    print("=" * 50)
    print("🎯 Focused Production Agent with Cloud Storage")
    print("=" * 50)

    # Load environment variables
    if Path(".env").exists():
        print("📋 Loading environment configuration...")
        with open(".env") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value
            print("✅ Environment configuration loaded")
    # Start health check service
    start_health_check()

    # Import and run Oracle Agent
    try:
        from oracle.agent_system import OracleAgent

        print("🤖 Initializing Oracle Agent...")
        agent = OracleAgent()

        print("🎯 Oracle Agent Production System Ready")
        print("📊 Health check: http://localhost:8080/health")
        print("📈 Metrics: http://localhost:8080/metrics")
        print("📋 Status: http://localhost:8080/status")

        # Check GCS integration
        if hasattr(agent, "gcs_backup_enabled") and agent.gcs_backup_enabled:
            print("☁️  GCS Storage: ENABLED - Cloud backups available")
        else:
            print("☁️  GCS Storage: DISABLED - Local storage only")

        print()
        # Check if running in production mode
        if os.environ.get("GCP_PROJECT_ID"):
            print("🔐 GCP Project ID configured - Full AI mode enabled")
            print(f"🧠 Running with model: {agent.cfg.model_id}")
        else:
            print("⚠️  No GCP Project ID - Running in demo mode")
            print("🔧 Configure GCP credentials for full AI functionality")
        print("💬 Starting optimized interactive session...")
        print("Commands: 'backup' (cloud), 'quit' to exit")
        print("-" * 50)

        # Interactive mode with enhanced features
        while True:
            try:
                prompt = input("👤 You: ").strip()
                if prompt.lower() in ["quit", "exit", "q"]:
                    print("👋 Goodbye!")
                    break

                if prompt.lower() == "backup":
                    if hasattr(agent, "backup_to_gcs"):
                        result = agent.backup_to_gcs()
                        if result["success"]:
                            print(f"✅ Backup successful: {result.get('gcs_uri', 'local')}")
                        else:
                            print(f"❌ Backup failed: {result.get('error')}")
                    else:
                        print("❌ Backup not available")
                    continue

                if prompt.lower() == "status":
                    print("📊 Oracle Agent Status:")
                    print(f"  Model: {agent.cfg.model_id}")
                    print(f"  GCS: {'Enabled' if agent.gcs_backup_enabled else 'Disabled'}")
                    print(f"  Max Turns: {agent.cfg.max_turns}")
                    continue

                if not prompt:
                    continue

                print("🤖 Oracle: Processing...")
                result = agent.run(prompt, "interactive_session")
                print(f"🤖 Oracle: {result}")
                print()

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                print("🔄 Please try again...")
                continue

    except Exception as e:
        print(f"❌ Failed to start Oracle Agent: {e}")
        return 1  # Reverted to original as the provided snippet was syntactically incorrect in this context

    return 0


def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals"""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    # Run main function
    sys.exit(main())
