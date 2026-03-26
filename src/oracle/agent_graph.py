import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .agent_system import PersistenceLayer
from .a2a_protocol import A2AMessage
from .safe_expression import SAFE_FUNCTIONS, evaluate_condition


@dataclass
class NodeHealth:
    status: str
    latency_ms: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeTask:
    task_id: str
    prompt: str
    context: Dict[str, Any]
    session_id: str
    parent_workflow_id: Optional[str] = None
    tools_override: Optional[List[str]] = None


@dataclass
class NodeResult:
    task_id: str
    node_id: str
    output: str
    tool_calls: List[Dict[str, Any]]
    success: bool
    latency_ms: float
    error: Optional[str] = None


class AgentNode(ABC):
    def __init__(self, node_id: str):
        self.node_id = node_id

    @abstractmethod
    async def run(self, task: NodeTask) -> NodeResult: ...

    async def on_message(self, msg: A2AMessage) -> None:
        return None

    async def health_check(self) -> NodeHealth:
        return NodeHealth(status="ok", latency_ms=0.0)


class EdgeType(str, Enum):
    DATA = "data"
    CONTROL = "control"
    CONDITIONAL = "conditional"


class AgentGraph:
    def __init__(self, registry: Any) -> None:
        self.registry = registry
        self.nodes: Dict[str, AgentNode] = {}
        self.edges: List[Dict[str, Any]] = []

    def add_node(self, node: AgentNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, from_id: str, to_id: str, edge_type: EdgeType) -> None:
        # Check for cycles
        if self._would_cause_cycle(from_id, to_id):
            raise ValueError(f"Adding edge {from_id} -> {to_id} would create a cycle.")
        self.edges.append({"from_id": from_id, "to_id": to_id, "type": edge_type})

    def _would_cause_cycle(self, from_id: str, to_id: str) -> bool:
        # Simple BFS/DFS to check for reachability from to_id to from_id
        visited = set()
        queue = [to_id]

        while queue:
            current = queue.pop(0)
            if current == from_id:
                return True
            visited.add(current)
            for edge in self.edges:
                if edge["from_id"] == current and edge["to_id"] not in visited:
                    queue.append(edge["to_id"])
        return False

    async def execute(self, workflow_def: "WorkflowDefinition", context: Dict[str, Any]) -> "WorkflowResult":
        return WorkflowResult(workflow_id=workflow_def.workflow_id, status=WorkflowStatus.COMPLETED, results={})

    def get_topology(self) -> Dict[str, Any]:
        return {"nodes": list(self.nodes.keys()), "edges": self.edges}


class ErrorStrategy(str, Enum):
    STOP = "STOP"
    CONTINUE = "CONTINUE"
    RETRY = "RETRY"


@dataclass
class WorkflowStep:
    step_id: str
    node_id: str
    condition: Optional[str] = None
    parallel_group: Optional[str] = None
    join_group: Optional[str] = None
    retry_count: int = 0
    timeout_s: float = 300.0


@dataclass
class WorkflowDefinition:
    workflow_id: str
    name: str
    steps: List[WorkflowStep]
    variables: Dict[str, Any]
    on_error: ErrorStrategy


class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class WorkflowResult:
    workflow_id: str
    status: WorkflowStatus
    results: Dict[str, NodeResult]
    error: Optional[str] = None


class WorkflowEngine:
    def __init__(self, graph: AgentGraph, persistence: PersistenceLayer) -> None:
        self.graph = graph
        self.persistence = persistence
        self._active_workflows: Dict[str, WorkflowStatus] = {}

    @staticmethod
    def _evaluate_condition(expression: str, variables: Dict[str, Any]) -> bool:
        """
        Evaluate a restricted workflow condition.

        Supported forms:
        - boolean / arithmetic expressions over workflow variables
        - comparisons, boolean operators, unary operators
        - a small allowlist of pure builtins
        """
        safe_context: Dict[str, Any] = {
            "True": True,
            "False": False,
            "None": None,
        }
        safe_context.update(variables)
        return evaluate_condition(expression, safe_context, SAFE_FUNCTIONS)

    async def run_workflow(self, definition: WorkflowDefinition) -> WorkflowResult:
        self._active_workflows[definition.workflow_id] = WorkflowStatus.RUNNING
        results: Dict[str, NodeResult] = {}

        try:
            for step in definition.steps:
                if self._active_workflows.get(definition.workflow_id) != WorkflowStatus.RUNNING:
                    break

                # Evaluation condition (SAFE: Use literal_eval instead of eval)
                if step.condition:
                    try:
                        condition_result = self._evaluate_condition(step.condition, definition.variables)
                        if not condition_result:
                            continue
                    except Exception as e:
                        if definition.on_error == ErrorStrategy.STOP:
                            raise ValueError(f"Unsafe or invalid condition '{step.condition}': {e}") from e
                        continue

                graph_node = self.graph.nodes.get(step.node_id)
                if not graph_node:
                    raise ValueError(f"Node {step.node_id} not found in graph")

                task = NodeTask(
                    task_id=f"{definition.workflow_id}_{step.step_id}",
                    prompt=definition.variables.get("prompt", ""),
                    context=definition.variables,
                    session_id=definition.workflow_id,
                    parent_workflow_id=definition.workflow_id,
                )

                for attempt in range(step.retry_count + 1):
                    try:
                        result = await asyncio.wait_for(graph_node.run(task), timeout=step.timeout_s)
                        results[step.step_id] = result
                        if not result.success and definition.on_error == ErrorStrategy.STOP:
                            self._active_workflows[definition.workflow_id] = WorkflowStatus.FAILED
                            return WorkflowResult(definition.workflow_id, WorkflowStatus.FAILED, results, result.error)
                        break
                    except Exception as e:
                        if attempt == step.retry_count:
                            if definition.on_error == ErrorStrategy.STOP:
                                self._active_workflows[definition.workflow_id] = WorkflowStatus.FAILED
                                return WorkflowResult(definition.workflow_id, WorkflowStatus.FAILED, results, str(e))

            current_status = self._active_workflows.get(definition.workflow_id, WorkflowStatus.COMPLETED)
            if current_status == WorkflowStatus.RUNNING:
                current_status = WorkflowStatus.COMPLETED

            self._active_workflows[definition.workflow_id] = current_status
            return WorkflowResult(definition.workflow_id, current_status, results)

        except Exception as e:
            self._active_workflows[definition.workflow_id] = WorkflowStatus.FAILED
            return WorkflowResult(definition.workflow_id, WorkflowStatus.FAILED, results, str(e))

    async def pause(self, workflow_id: str) -> None:
        if workflow_id in self._active_workflows:
            self._active_workflows[workflow_id] = WorkflowStatus.PAUSED

    async def resume(self, workflow_id: str) -> None:
        if workflow_id in self._active_workflows and self._active_workflows[workflow_id] == WorkflowStatus.PAUSED:
            self._active_workflows[workflow_id] = WorkflowStatus.RUNNING

    async def cancel(self, workflow_id: str) -> None:
        if workflow_id in self._active_workflows:
            self._active_workflows[workflow_id] = WorkflowStatus.CANCELLED

    def get_status(self, workflow_id: str) -> WorkflowStatus:
        return self._active_workflows.get(workflow_id, WorkflowStatus.PENDING)
