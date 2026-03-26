"""
Oracle Agent Workflow Engine - Enterprise Automation
"""

from __future__ import annotations

import asyncio
import os
import subprocess  # nosec B404 - explicit workflow shell execution remains behind an opt-in gate
import uuid
from datetime import datetime
from enum import Enum
from shutil import which
from typing import Any

import requests

from .network_guard import HTTP_REDIRECT_BLOCKED_ERROR, validate_outbound_http_url
from .safe_expression import evaluate_condition


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowEngine:
    def __init__(self) -> None:
        self.workflows: dict[str, dict[str, Any]] = {}
        self.executions: dict[str, dict[str, Any]] = {}

    def create_workflow(self, name: str, steps: list[dict[str, Any]]) -> str:
        """Create a new workflow."""
        workflow_id = str(uuid.uuid4())
        self.workflows[workflow_id] = {
            "id": workflow_id,
            "name": name,
            "steps": steps,
            "created_at": datetime.now().isoformat(),
        }
        return workflow_id

    async def execute_workflow(
        self,
        workflow_id: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        execution_id = str(uuid.uuid4())
        execution: dict[str, Any] = {
            "id": execution_id,
            "workflow_id": workflow_id,
            "status": WorkflowStatus.RUNNING.value,
            "started_at": datetime.now().isoformat(),
            "context": context or {},
        }
        self.executions[execution_id] = execution

        try:
            results: list[Any] = []
            for step in workflow["steps"]:
                result = await self._execute_step(step, execution["context"])
                results.append(result)

            execution["status"] = WorkflowStatus.COMPLETED.value
            execution["results"] = results
            execution["completed_at"] = datetime.now().isoformat()
            return execution
        except Exception as e:
            execution["status"] = WorkflowStatus.FAILED.value
            execution["error"] = str(e)
            raise

    async def _execute_step(self, step: dict[str, Any], context: dict[str, Any]) -> Any:
        """Execute a single workflow step."""
        step_type = str(step.get("type", "task"))

        if step_type == "shell":
            return await self._execute_shell_step(step, context)
        if step_type == "api":
            return await self._execute_api_step(step, context)
        if step_type == "decision":
            return await self._execute_decision_step(step, context)
        return {"result": f"Executed {step_type} step"}

    async def _execute_shell_step(
        self,
        step: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute shell command step."""
        del context
        if os.environ.get("ORACLE_ENABLE_WORKFLOW_SHELL", "").strip().lower() != "true":
            raise ValueError("Shell workflow steps are disabled by default")

        shell_executable = which("bash")
        if not shell_executable:
            raise RuntimeError("bash executable not found")

        command = str(step.get("command", "echo 'Hello World'"))
        result = await asyncio.to_thread(
            subprocess.run,  # nosec B603 - explicitly opt-in shell workflow execution
            [shell_executable, "-lc", command],
            capture_output=True,
            text=True,
            check=False,
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}

    async def _execute_api_step(
        self,
        step: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute API call step."""
        del context
        url = str(step.get("url", "https://httpbin.org/get"))
        method = str(step.get("method", "GET"))
        error = validate_outbound_http_url(url)
        if error:
            raise ValueError(error)
        response = await asyncio.to_thread(requests.request, method, url, timeout=15, allow_redirects=False)
        if 300 <= response.status_code < 400:
            raise ValueError(HTTP_REDIRECT_BLOCKED_ERROR)
        data: Any
        try:
            data = response.json()
        except ValueError:
            data = response.text
        return {"status_code": response.status_code, "data": data}

    async def _execute_decision_step(
        self,
        step: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute decision step with a restricted expression evaluator."""
        condition = str(step.get("condition", "True"))
        try:
            if self._safe_eval(condition, context):
                return {"decision": "true", "next": step.get("true_path")}
            return {"decision": "false", "next": step.get("false_path")}
        except Exception:
            return {"decision": "error", "next": step.get("default_path")}

    @staticmethod
    def _safe_eval(condition: str, context: dict[str, Any]) -> bool:
        """Evaluate a simple boolean expression over the provided context."""
        safe_context = {"True": True, "False": False, "None": None}
        safe_context.update(context)
        return evaluate_condition(condition, safe_context)

    def get_workflow_status(self, execution_id: str) -> dict[str, Any] | None:
        """Get workflow execution status."""
        return self.executions.get(execution_id)
