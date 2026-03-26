"""
Oracle Agent Workflow Engine - Enterprise Automation
"""

from __future__ import annotations

import ast
import asyncio
import subprocess
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

import requests


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
        command = str(step.get("command", "echo 'Hello World'"))
        result = await asyncio.to_thread(
            subprocess.run,
            ["bash", "-lc", command],
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
        response = await asyncio.to_thread(requests.request, method, url)
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
        try:
            literal_value = ast.literal_eval(condition)
        except (ValueError, SyntaxError):
            literal_value = None
        else:
            return bool(literal_value)

        tree = ast.parse(condition, mode="eval")
        allowed_nodes = (
            ast.Expression,
            ast.BoolOp,
            ast.BinOp,
            ast.UnaryOp,
            ast.Compare,
            ast.Name,
            ast.Load,
            ast.Constant,
            ast.And,
            ast.Or,
            ast.Not,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Mod,
            ast.Pow,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
        )
        allowed_names = set(context.keys()) | {"True", "False", "None"}

        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise ValueError(f"Unsafe syntax: {type(node).__name__}")
            if isinstance(node, ast.Name) and node.id not in allowed_names:
                raise ValueError(f"Unsafe variable access: {node.id}")

        return bool(eval(compile(tree, "<workflow_condition>", "eval"), {"__builtins__": {}}, context))

    def get_workflow_status(self, execution_id: str) -> dict[str, Any] | None:
        """Get workflow execution status."""
        return self.executions.get(execution_id)
