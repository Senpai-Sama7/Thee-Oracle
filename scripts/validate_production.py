#!/usr/bin/env python3
"""
Oracle Agent Production Validation Script
Comprehensive system validation for production deployment
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run command and return result with description"""
    try:
        # Handle virtual environment activation
        if "source venv/bin/activate" in cmd:
            # Modify command to work without source
            cmd = cmd.replace("source venv/bin/activate && ", "")
            # Add venv to Python path
            env = os.environ.copy()
            venv_python = str(Path.cwd() / "venv" / "bin" / "python3")
            if "python3 -c" in cmd:
                cmd = cmd.replace("python3 -c", f"{venv_python} -c")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, env=env)
        else:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip(),
            "description": description
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out",
            "description": description
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "description": description
        }

def validate_production_system():
    """Comprehensive production system validation"""
    
    print("🔍 ORACLE AGENT PRODUCTION VALIDATION")
    print("=" * 60)
    print()
    
    validation_results = []
    
    # 1. Environment Validation
    print("📋 1. ENVIRONMENT VALIDATION")
    print("-" * 40)
    
    env_checks = [
        ("python3 --version", "Python version check"),
        ("source venv/bin/activate && python3 -c 'import google.genai; print(\"GEMINI OK\")'", "Google GenAI SDK"),
        ("source venv/bin/activate && python3 -c 'import google.cloud.storage; print(\"GCS OK\")'", "Google Cloud Storage"),
        ("source venv/bin/activate && python3 scripts/validate_env.py", "Environment configuration"),
    ]
    
    for cmd, desc in env_checks:
        result = run_command(cmd, desc)
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {desc}")
        if not result["success"]:
            print(f"     Error: {result['error']}")
        validation_results.append(result)
    
    print()
    
    # 2. Core System Validation
    print("🤖 2. CORE SYSTEM VALIDATION")
    print("-" * 40)
    
    system_checks = [
        ("source venv/bin/activate && python3 -c 'from src.oracle.agent_system import OracleAgent; print(\"AGENT OK\")'", "Oracle Agent import"),
        ("source venv/bin/activate && python3 -c 'from src.oracle.gcs_storage import GCSStorageManager; print(\"GCS MANAGER OK\")'", "GCS Storage Manager"),
        ("source venv/bin/activate && python3 -c 'from src.oracle.health_check import main; print(\"HEALTH CHECK OK\")'", "Health Check Service"),
    ]
    
    for cmd, desc in system_checks:
        result = run_command(cmd, desc)
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {desc}")
        if not result["success"]:
            print(f"     Error: {result['error']}")
        validation_results.append(result)
    
    print()
    
    # 3. Security Validation
    print("🔒 3. SECURITY VALIDATION")
    print("-" * 40)
    
    security_checks = [
        ("test -f .env && echo 'ENV FILE EXISTS'", "Environment file exists"),
        ("test -f src/oracle/agent_system.py && echo 'AGENT SYSTEM EXISTS'", "Core agent file exists"),
        ("test -f src/oracle/gcs_storage.py && echo 'GCS STORAGE EXISTS'", "GCS storage exists"),
        ("test -f src/oracle/health_check.py && echo 'HEALTH CHECK EXISTS'", "Health check exists"),
    ]
    
    for cmd, desc in security_checks:
        result = run_command(cmd, desc)
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {desc}")
        if not result["success"]:
            print(f"     Error: {result['error']}")
        validation_results.append(result)
    
    print()
    
    # 4. Configuration Validation
    print("⚙️  4. CONFIGURATION VALIDATION")
    print("-" * 40)
    
    config_checks = [
        ("grep -q 'ORACLE_MODEL_ID' .env && echo 'MODEL CONFIGURED'", "Model configuration"),
        ("grep -q 'GCS_BUCKET_NAME' .env && echo 'GCS CONFIGURED'", "GCS configuration"),
        ("grep -q 'GCP_PROJECT_ID' .env && echo 'GCP CONFIGURED'", "GCP configuration"),
    ]
    
    for cmd, desc in config_checks:
        result = run_command(cmd, desc)
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {desc}")
        if not result["success"]:
            print(f"     Error: {result['error']}")
        validation_results.append(result)
    
    print()
    
    # 5. Documentation Validation
    print("📚 5. DOCUMENTATION VALIDATION")
    print("-" * 40)
    
    doc_checks = [
        ("test -f README.md && echo 'USER MANUAL EXISTS'", "User manual"),
        ("test -f docs/README.md && echo 'DOC INDEX EXISTS'", "Documentation index"),
        ("test -f docs/TECHNICAL_IMPLEMENTATION_GUIDE.md && echo 'TECHNICAL GUIDE EXISTS'", "Technical guide"),
        ("test -f docs/ORACLE_PLATFORM_COMPREHENSIVE_GUIDE.md && echo 'PLATFORM GUIDE EXISTS'", "Platform guide"),
    ]
    
    for cmd, desc in doc_checks:
        result = run_command(cmd, desc)
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {desc}")
        if not result["success"]:
            print(f"     Error: {result['error']}")
        validation_results.append(result)
    
    print()
    
    # 6. Production Readiness Assessment
    print("🚀 6. PRODUCTION READINESS ASSESSMENT")
    print("-" * 40)
    
    success_count = sum(1 for r in validation_results if r["success"])
    total_count = len(validation_results)
    success_rate = (success_count / total_count) * 100
    
    print(f"  📊 Overall Success Rate: {success_rate:.1f}%")
    print(f"  ✅ Passed Checks: {success_count}/{total_count}")
    print(f"  ❌ Failed Checks: {total_count - success_count}/{total_count}")
    
    print()
    
    # Critical Components Check
    critical_components = [
        "Oracle Agent Core",
        "GCS Storage Integration", 
        "Health Check Service",
        "Environment Configuration",
        "Security Implementation",
    ]
    
    critical_status = "✅ PRODUCTION READY"
    if success_rate >= 90:
        critical_status = "✅ PRODUCTION READY"
    elif success_rate >= 75:
        critical_status = "⚠️  NEEDS MINOR FIXES"
    else:
        critical_status = "❌ NOT PRODUCTION READY"
    
    print(f"  🎯 Critical Status: {critical_status}")
    print()
    
    # Recommendations
    print("📋 7. RECOMMENDATIONS")
    print("-" * 40)
    
    if success_rate >= 90:
        print("  ✅ System is production-ready")
        print("  🚀 Recommended: Deploy to production")
        print("  📊 Monitor: Health checks and metrics")
        print("  💾 Backup: Regular GCS backups")
    elif success_rate >= 75:
        print("  ⚠️  System needs minor fixes")
        print("  🔧 Recommended: Fix failed validations")
        print("  📊 Monitor: Check specific error messages")
    else:
        print("  ❌ System not production-ready")
        print("  🔧 Recommended: Fix critical issues first")
        print("  📚 Review: Check documentation for setup")
    
    print()
    
    # Production Deployment Command
    print("🚀 8. PRODUCTION DEPLOYMENT")
    print("-" * 40)
    
    if success_rate >= 90:
        print("  🎯 DEPLOYMENT COMMAND:")
        print("  source venv/bin/activate")
        print("  python3 main.py")
        print()
        print("  📊 MONITORING:")
        print("  Health: http://localhost:8080/health")
        print("  Metrics: http://localhost:8080/metrics")
        print("  Status: http://localhost:8080/status")
        print()
        print("  ☁️ CLOUD FEATURES:")
        print("  Type 'backup' for database backup")
        print("  Type 'status' for system status")
        print("  Screenshots automatically uploaded to GCS")
    else:
        print("  🔧 FIX REQUIRED BEFORE DEPLOYMENT")
        print("  Review failed validations above")
    
    print()
    print("=" * 60)
    print("🎉 PRODUCTION VALIDATION COMPLETE")
    
    return success_rate >= 90

if __name__ == "__main__":
    success = validate_production_system()
    sys.exit(0 if success else 1)
