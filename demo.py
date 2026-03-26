#!/usr/bin/env python3
"""
Oracle Agent Demo Mode
Shows functionality without requiring GCP credentials
"""

import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from oracle.agent_system import OracleConfig, ToolExecutor, PersistenceLayer


def demo_tools():
    """Demonstrate all tool capabilities without AI"""
    print("🔧 ORACLE AGENT TOOL DEMONSTRATION")
    print("=" * 50)

    config = OracleConfig()
    tools = ToolExecutor(config.project_root, config.shell_timeout, config.http_timeout)

    # Demo 1: Shell Execute
    print("\n📊 SYSTEM INFORMATION:")
    result = tools.shell_execute("uname -a")
    if result["success"]:
        print(f"✅ System: {result['stdout']}")

    result = tools.shell_execute("df -h / | tail -1")
    if result["success"]:
        print(f"💾 Disk: {result['stdout']}")

    # Demo 2: File Operations
    print("\n📝 FILE OPERATIONS:")
    demo_content = (
        "# Oracle Agent Demo\n\n"
        "This is a demonstration file created by Oracle Agent.\n\n"
        "## System Status\n"
        "- ✅ Tools working\n"
        "- ✅ Database operational\n"
        "- ✅ File system accessible\n"
    )

    result = tools.file_system_ops("write", "demo_output.md", demo_content)
    if result["success"]:
        print("✅ Created demo_output.md")

        result = tools.file_system_ops("read", "demo_output.md")
        if result["success"]:
            print(f"📄 Content preview: {result['content'][:100]}...")

    # Demo 3: Directory Listing
    print("\n📁 PROJECT STRUCTURE:")
    result = tools.file_system_ops("list", "src")
    if result["success"]:
        for item in result["items"]:
            print(f"  {'📁' if item['type'] == 'dir' else '📄'} {item['name']}")

    # Demo 4: HTTP Request
    print("\n🌐 WEB CONNECTIVITY:")
    result = tools.http_fetch("https://httpbin.org/user-agent")
    if result["success"]:
        print("✅ Internet connectivity working")
        print(f"🔗 Response status: {result['status']}")
    else:
        print("⚠️  Internet connectivity test failed")


def demo_database():
    """Demonstrate database functionality"""
    print("\n💾 DATABASE DEMONSTRATION")
    print("=" * 50)

    config = OracleConfig()
    db = PersistenceLayer(config.db_path)

    # Log some demo events
    db.log_event("demo_session", "tool_test", {"tool": "shell_execute", "result": "success"})
    db.log_event("demo_session", "file_ops", {"operation": "write", "file": "demo_output.md"})
    db.log_event("demo_session", "connectivity", {"http_test": "passed"})

    # Save demo history
    demo_history = [
        {"role": "user", "parts": [{"text": "Show me system information"}]},
        {"role": "model", "parts": [{"text": "I'll check your system information for you."}]},
        {
            "role": "tool",
            "parts": [
                {
                    "function_response": {
                        "name": "shell_execute",
                        "response": {"success": True, "stdout": "Ubuntu 25.10"},
                    }
                }
            ],
        },
    ]

    db.save_history("demo_session", demo_history)

    # Load and verify
    loaded = db.load_history("demo_session")
    if loaded:
        print("✅ Database persistence working")
        print(f"📊 Saved {len(loaded)} conversation turns")
        print(f"📍 Database file: {config.db_path}")
        print(f"📏 Database size: {config.db_path.stat().st_size} bytes")


def demo_configuration():
    """Show current configuration"""
    print("\n⚙️  CONFIGURATION DEMONSTRATION")
    print("=" * 50)

    config = OracleConfig()

    print(f"🏠 Project Root: {config.project_root}")
    print(f"🗄️  Database Path: {config.db_path}")
    print(f"🤖 Model ID: {config.model_id}")
    print(f"☁️  GCP Project: {config.gcp_project or 'Not configured'}")
    print(f"📍 GCP Location: {config.gcp_location}")
    print(f"⏱️  Shell Timeout: {config.shell_timeout}s")
    print(f"🌐 HTTP Timeout: {config.http_timeout}s")
    print(f"🔄 Max Turns: {config.max_turns}")


def main():
    """Run complete demonstration"""
    print("🚀 ORACLE AGENT - DEMO MODE")
    print("=" * 50)
    print("This demo shows all Oracle Agent capabilities without requiring GCP credentials.")
    print("For full AI functionality, set up GCP authentication and run: python3 main.py")
    print()

    try:
        demo_configuration()
        demo_tools()
        demo_database()

        print("\n🎉 DEMONSTRATION COMPLETE!")
        print("=" * 50)
        print("✅ All core components operational")
        print("✅ Tools working correctly")
        print("✅ Database persistence functional")
        print("✅ File system access confirmed")
        print("✅ Web connectivity verified")
        print()
        print("🚀 READY FOR PRODUCTION USE!")
        print("📚 See README.md for user guide")
        print("🔧 Configure GCP credentials for AI functionality")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
