#!/usr/bin/env python3
"""
Oracle Agent production validation script.

This validator avoids shell-string execution and relies on explicit subprocess
argument lists plus direct filesystem inspection.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


@dataclass
class ValidationResult:
    success: bool
    description: str
    output: str = ""
    error: str = ""


def project_python() -> str:
    venv_python = PROJECT_ROOT / "venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def run_command(args: list[str], description: str) -> ValidationResult:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
            check=False,
            env=os.environ.copy(),
        )
        return ValidationResult(
            success=result.returncode == 0,
            description=description,
            output=result.stdout.strip(),
            error=result.stderr.strip(),
        )
    except subprocess.TimeoutExpired:
        return ValidationResult(success=False, description=description, error="Command timed out")
    except Exception as exc:
        return ValidationResult(success=False, description=description, error=str(exc))


def file_contains(path: Path, needle: str) -> bool:
    return path.exists() and needle in path.read_text()


def path_check(path: Path, description: str) -> ValidationResult:
    return ValidationResult(success=path.exists(), description=description, output=str(path))


def config_check(needle: str, description: str) -> ValidationResult:
    return ValidationResult(
        success=file_contains(ENV_PATH, f"{needle}="),
        description=description,
        output=needle,
        error="" if ENV_PATH.exists() else ".env file not found",
    )


def validate_production_system() -> bool:
    print("Oracle Agent Production Validation")
    print("=" * 60)
    print()

    python_bin = project_python()
    validation_results: list[ValidationResult] = []

    print("1. Environment Validation")
    print("-" * 40)
    env_checks = [
        run_command([sys.executable, "--version"], "Python version check"),
        run_command([python_bin, "-c", "import google.genai; print('GEMINI OK')"], "Google GenAI SDK"),
        run_command([python_bin, "-c", "import google.cloud.storage; print('GCS OK')"], "Google Cloud Storage"),
        run_command([python_bin, "scripts/validate_env.py"], "Environment configuration"),
    ]
    for result in env_checks:
        status = "OK" if result.success else "FAIL"
        print(f"  [{status}] {result.description}")
        if not result.success and result.error:
            print(f"        {result.error}")
        validation_results.append(result)
    print()

    print("2. Core System Validation")
    print("-" * 40)
    system_checks = [
        run_command(
            [python_bin, "-c", "from src.oracle.agent_system import OracleAgent; print('AGENT OK')"],
            "Oracle Agent import",
        ),
        run_command(
            [python_bin, "-c", "from src.oracle.gcs_storage import GCSStorageManager; print('GCS MANAGER OK')"],
            "GCS Storage Manager",
        ),
        run_command(
            [python_bin, "-c", "from src.oracle.health_check import main; print('HEALTH CHECK OK')"],
            "Health Check Service",
        ),
    ]
    for result in system_checks:
        status = "OK" if result.success else "FAIL"
        print(f"  [{status}] {result.description}")
        if not result.success and result.error:
            print(f"        {result.error}")
        validation_results.append(result)
    print()

    print("3. Security Validation")
    print("-" * 40)
    security_checks = [
        path_check(ENV_PATH, "Environment file exists"),
        path_check(PROJECT_ROOT / "src/oracle/agent_system.py", "Core agent file exists"),
        path_check(PROJECT_ROOT / "src/oracle/gcs_storage.py", "GCS storage exists"),
        path_check(PROJECT_ROOT / "src/oracle/health_check.py", "Health check exists"),
    ]
    for result in security_checks:
        status = "OK" if result.success else "FAIL"
        print(f"  [{status}] {result.description}")
        if not result.success and result.error:
            print(f"        {result.error}")
        validation_results.append(result)
    print()

    print("4. Configuration Validation")
    print("-" * 40)
    configuration_checks = [
        config_check("ORACLE_MODEL_ID", "Model configuration"),
        config_check("GCS_BUCKET_NAME", "GCS configuration"),
        config_check("GCP_PROJECT_ID", "GCP configuration"),
    ]
    for result in configuration_checks:
        status = "OK" if result.success else "FAIL"
        print(f"  [{status}] {result.description}")
        if not result.success and result.error:
            print(f"        {result.error}")
        validation_results.append(result)
    print()

    print("5. Documentation Validation")
    print("-" * 40)
    doc_checks = [
        path_check(PROJECT_ROOT / "README.md", "User manual"),
        path_check(PROJECT_ROOT / "docs/README.md", "Documentation index"),
        path_check(PROJECT_ROOT / "docs/TECHNICAL_IMPLEMENTATION_GUIDE.md", "Technical guide"),
        path_check(PROJECT_ROOT / "docs/ORACLE_PLATFORM_COMPREHENSIVE_GUIDE.md", "Platform guide"),
    ]
    for result in doc_checks:
        status = "OK" if result.success else "FAIL"
        print(f"  [{status}] {result.description}")
        if not result.success and result.error:
            print(f"        {result.error}")
        validation_results.append(result)
    print()

    success_count = sum(1 for result in validation_results if result.success)
    total_count = len(validation_results)
    success_rate = (success_count / total_count) * 100 if total_count else 0.0

    print("6. Production Readiness Assessment")
    print("-" * 40)
    print(f"  Success rate: {success_rate:.1f}%")
    print(f"  Passed checks: {success_count}/{total_count}")
    print(f"  Failed checks: {total_count - success_count}/{total_count}")
    print()

    if success_rate >= 90:
        readiness = "PRODUCTION READY"
    elif success_rate >= 75:
        readiness = "NEEDS MINOR FIXES"
    else:
        readiness = "NOT PRODUCTION READY"
    print(f"  Status: {readiness}")
    print()

    print("7. Recommendations")
    print("-" * 40)
    if success_rate >= 90:
        print("  - Deploy with the validated runtime entrypoints.")
        print("  - Keep health and metrics endpoints monitored.")
        print("  - Back up SQLite state to GCS if configured.")
    elif success_rate >= 75:
        print("  - Fix failed validations before promoting to production.")
        print("  - Re-run this validator and the test suite after changes.")
    else:
        print("  - Do not deploy yet.")
        print("  - Fix environment and runtime issues first.")
    print()

    print("8. Production Deployment")
    print("-" * 40)
    if success_rate >= 90:
        print(f"  {python_bin} main.py")
        print("  Health: http://localhost:8080/health")
        print("  Metrics: http://localhost:8080/metrics")
        print("  Status: http://localhost:8080/status")
    else:
        print("  Deployment blocked until failed checks are resolved.")
    print()

    print("=" * 60)
    print("Production validation complete")
    return success_rate >= 90


if __name__ == "__main__":
    raise SystemExit(0 if validate_production_system() else 1)
