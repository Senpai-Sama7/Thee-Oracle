#!/usr/bin/env python3
"""
Oracle Agent Environment Configuration Validator
Validates and reports on all .env variable utilization
"""

import os
import sys
from pathlib import Path

def validate_env_variables():
    """Validate all environment variables are properly configured"""
    # Environment validation for Oracle Agent configuration
    print("🔍 ORACLE AGENT ENVIRONMENT VALIDATION") 
    print("=" * 60)
    
    # Load .env file
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        return False
    
    # Parse .env variables
    env_vars = {}
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key] = value
    
    print(f"📋 Found {len(env_vars)} environment variables")
    print()
    
    # Core GCP Configuration
    print("🔐 CORE GCP CONFIGURATION:")
    gcp_vars = [
        "GCP_PROJECT_ID",
        "GCP_PROJECT_NAME", 
        "GCP_PROJECT_NUMBER",
        "GCP_REGION",
        "GCP_LOCATION",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_CLOUD_API_KEY"
    ]
    
    for var in gcp_vars:
        value = env_vars.get(var, "NOT SET")
        status = "✅" if value != "NOT SET" and value != "" else "❌"
        print(f"  {status} {var}: {value[:50]}{'...' if len(value) > 50 else ''}")
    
    print()
    
    # Oracle Agent Configuration
    print("🤖 ORACLE AGENT CONFIGURATION:")
    oracle_vars = [
        "ORACLE_PROJECT_ROOT",
        "ORACLE_MODEL_ID",
        "ORACLE_MAX_TURNS",
        "ORACLE_SHELL_TIMEOUT",
        "ORACLE_HTTP_TIMEOUT",
        "ORACLE_LOG_LEVEL"
    ]
    
    for var in oracle_vars:
        value = env_vars.get(var, "NOT SET")
        status = "✅" if value != "NOT SET" and value != "" else "❌"
        print(f"  {status} {var}: {value}")
    
    print()
    
    # Database Configuration
    print("💾 DATABASE CONFIGURATION:")
    db_vars = [
        "DATABASE_URL",
        "GCP_DATABASE_ID"
    ]
    
    for var in db_vars:
        value = env_vars.get(var, "NOT SET")
        status = "✅" if value != "NOT SET" and value != "" else "❌"
        print(f"  {status} {var}: {value}")
    
    print()
    
    # Storage Configuration
    print("🪣 STORAGE CONFIGURATION:")
    storage_vars = [
        "GCS_BUCKET_NAME",
        "RABBITMQ_URL",
        "RABBITMQ_QUEUE",
        "RABBITMQ_EXCHANGE"
    ]
    
    for var in storage_vars:
        value = env_vars.get(var, "NOT SET")
        status = "✅" if value != "NOT SET" and value != "" else "❌"
        print(f"  {status} {var}: {value}")
    
    print()
    
    # Discovery Engine Configuration
    print("🔍 DISCOVERY ENGINE CONFIGURATION:")
    discovery_vars = [
        "DISCOVERY_ENGINE_ID",
        "GCP_DATA_STORE_ID"
    ]
    
    for var in discovery_vars:
        value = env_vars.get(var, "NOT SET")
        status = "✅" if value != "NOT SET" and value != "" else "❌"
        print(f"  {status} {var}: {value}")
    
    print()
    
    # Monitoring Configuration
    print("📊 MONITORING CONFIGURATION:")
    monitoring_vars = [
        "PROMETHEUS_PORT",
        "METRICS_ENABLED",
        "HEALTH_CHECK_PORT"
    ]
    
    for var in monitoring_vars:
        value = env_vars.get(var, "NOT SET")
        status = "✅" if value != "NOT SET" and value != "" else "❌"
        print(f"  {status} {var}: {value}")
    
    print()
    
    # Security Configuration
    print("🔒 SECURITY CONFIGURATION:")
    security_vars = [
        "ENABLE_AUTHENTICATION",
        "API_KEY",
        "JWT_SECRET"
    ]
    
    for var in security_vars:
        value = env_vars.get(var, "NOT SET")
        status = "✅" if value != "NOT SET" and value != "" else "❌"
        print(f"  {status} {var}: {value}")
    
    print()
    
    # Performance Configuration
    print("⚡ PERFORMANCE CONFIGURATION:")
    perf_vars = [
        "MAX_CONCURRENT_SESSIONS",
        "SESSION_TIMEOUT",
        "CACHE_TTL"
    ]
    
    for var in perf_vars:
        value = env_vars.get(var, "NOT SET")
        status = "✅" if value != "NOT SET" and value != "" else "❌"
        print(f"  {status} {var}: {value}")
    
    print()
    
    # Safe Services Configuration
    print("🛡️  SAFE SERVICES CONFIGURATION:")
    safe_vars = [
        "SAFE_GCP_SERVICES"
    ]
    
    for var in safe_vars:
        value = env_vars.get(var, "NOT SET")
        status = "✅" if value != "NOT SET" and value != "" else "❌"
        print(f"  {status} {var}: {value[:60]}{'...' if len(value) > 60 else ''}")
    
    print()
    
    # Summary
    total_vars = len(env_vars)
    set_vars = sum(1 for v in env_vars.values() if v != "" and v != "NOT SET")
    print("📊 CONFIGURATION SUMMARY:")
    print(f"  • Total variables: {total_vars}")
    print(f"  • Configured: {set_vars}")
    print(f"  • Missing: {total_vars - set_vars}")
    print(f"  • Completion: {(set_vars/total_vars)*100:.1f}%")
    # Critical requirements check
    critical_vars = ["GCP_PROJECT_ID", "ORACLE_MODEL_ID", "GOOGLE_API_KEY"]
    missing_critical = [v for v in critical_vars if env_vars.get(v, "") == ""]
    
    if not missing_critical:
        print(" ALL CRITICAL VARIABLES CONFIGURED")
        print(" Oracle Agent is ready for production use!")
        print("🚀 Oracle Agent is ready for production use!")
    else:
        print(f"❌ MISSING CRITICAL VARIABLES: {', '.join(missing_critical)}")
        print("🔧 Please configure these variables before production use")
    
    return len(missing_critical) == 0

if __name__ == "__main__":
    # Set environment variables from .env
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
    
    success = validate_env_variables()
    sys.exit(0 if success else 1)
