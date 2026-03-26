#!/usr/bin/env python3
"""
Oracle Agent GUI Launcher
Handles dependency checking and launches the web interface
"""

import sys
import subprocess


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


def install_dependencies(missing):
    """Install missing dependencies."""
    print(f"📦 Installing missing dependencies: {', '.join(missing)}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False


def main():
    """Launch the Oracle Agent GUI."""
    print("🚀 Oracle Agent GUI Launcher")
    print("=" * 50)

    # Check dependencies
    missing = check_dependencies()
    if missing:
        print(f"⚠️  Missing dependencies: {', '.join(missing)}")
        response = input("Install now? (y/n): ").strip().lower()
        if response == "y":
            if not install_dependencies(missing):
                sys.exit(1)
        else:
            print("❌ Cannot launch without dependencies")
            sys.exit(1)

    # Launch the GUI
    print("🌐 Starting Oracle Agent GUI...")
    print("📍 URL: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop")
    print("=" * 50)

    try:
        from gui.app import app, socketio

        socketio.run(app, host="0.0.0.0", port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n👋 GUI stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
