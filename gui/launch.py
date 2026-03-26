#!/usr/bin/env python3
"""
Oracle Agent GUI Launcher
Handles dependency checking and launches the web interface
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check_dependencies():
    """Check if required packages are installed."""
    required = ["flask", "flask_socketio"]
    missing = []

    for package in required:
        try:
            # SAFE: Use importlib.import_module instead of __import__
            import importlib

            importlib.import_module(package.replace("-", "_"))
        except ImportError:
            missing.append(package)

    return missing


def main():
    """Launch the Oracle Agent GUI."""
    gui_host = os.environ.get("ORACLE_GUI_HOST", "127.0.0.1").strip() or "127.0.0.1"
    gui_port = int(os.environ.get("ORACLE_GUI_PORT", "5001"))

    print("🚀 Oracle Agent GUI Launcher")
    print("=" * 50)

    # Check dependencies
    missing = check_dependencies()
    if missing:
        print(f"⚠️  Missing dependencies: {', '.join(missing)}")
        print(f"Install them first, for example: {sys.executable} -m pip install {' '.join(missing)}")
        sys.exit(1)

    # Launch the GUI
    print("🌐 Starting Oracle Agent GUI...")
    print(f"📍 URL: http://{gui_host}:{gui_port}")
    print("⏹️  Press Ctrl+C to stop")
    print("=" * 50)

    try:
        from gui.app import app, create_gui_directories, initialize_agent, socketio

        create_gui_directories()
        if initialize_agent():
            print("✅ Oracle Agent initialized")
        else:
            print("⚠️  Oracle Agent failed to initialize; GUI will show error state")

        socketio.run(app, host=gui_host, port=gui_port, debug=False)
    except KeyboardInterrupt:
        print("\n👋 GUI stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
