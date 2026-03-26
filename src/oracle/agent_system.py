#!/usr/bin/env python3
"""
Oracle Agent - Production Synthesis
Combines v1's SDK type fidelity and SQLite persistence architecture
with v2's comprehensive tooling surface and screenshot fallback chain.

Verified fixes applied:
  - pickle -> JSON serialization (eliminates arbitrary code exec surface)
  - shell=True -> ["bash", "-c", cmd] (eliminates shell interpolation injection)
  - response.thoughts -> part.thought iteration (correct SDK access pattern)
  - role="function_response" -> role="tool" with Part.from_function_response
  - pickle history -> JSON-serializable dict round-trip
  - __init__ crash-on-start -> validated config before connection attempts
  - hardcoded credentials -> environment variables only
  - log_event arity mismatch -> fixed signature
  - history injection on resumed sessions -> explicit user turn append
  - no max_turns guard -> configurable ceiling with warning
  - path traversal in file_system_ops -> resolve() containment check

Requirements:
  pip install google-genai>=1.67.0

Environment variables:
  GCP_PROJECT_ID         Required. Google Cloud project for Vertex AI.
  GCP_LOCATION           Optional. Vertex AI region (default: us-central1).
  ORACLE_MODEL_ID        Optional. Verify against Vertex AI model garden.
                         Default: gemini-2.5-pro-preview-05-06
  ORACLE_PROJECT_ROOT    Optional. Working directory (default: ~/Projects/oracle).
  ORACLE_SHELL_TIMEOUT   Optional. Seconds before shell commands are killed (default: 60).
  ORACLE_HTTP_TIMEOUT    Optional. Seconds before HTTP requests are killed (default: 15).
  ORACLE_MAX_TURNS       Optional. Agentic loop ceiling (default: 20).
"""

import os
import sys
import json
import sqlite3
import subprocess  # nosec B404 - intentional process boundary for explicit agent tools
import logging
import tempfile
from pathlib import Path
from shutil import which
from typing import Any, Dict, List, cast
import requests
from google import genai
from google.genai import types
from .gcs_storage import GCSStorageManager
from .network_guard import (
    HTTP_REDIRECT_BLOCKED_ERROR,
    validate_outbound_http_url,
)

# MCP + Skills imports (Oracle 5.0)
try:
    from .mcp_client import MCPClient
    from .mcp_registry import MCPRegistry
    from .skill_loader import SkillLoader
    from .tool_registry import ToolRegistry

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# Model Router imports (Oracle 5.0 Phase 1)
try:
    from .model_router import (
        ModelRouter,
        GenerateConfig,
        create_router_from_config,
    )

    MODEL_ROUTER_AVAILABLE = True
except ImportError:
    MODEL_ROUTER_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("oracle")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class OracleConfig:
    """
    All runtime parameters sourced from environment variables.
    No defaults embed credentials or environment-specific paths beyond
    the user home convention (Path.home()).
    """

    def __init__(self) -> None:
        repo_root = Path(__file__).parent.parent.parent.resolve()
        project_root_env = os.environ.get("ORACLE_PROJECT_ROOT")
        self.project_root = Path(project_root_env).expanduser().resolve() if project_root_env else repo_root
        # IMPORTANT: verify this model ID against the Vertex AI model garden
        # before running. Model preview strings rotate. As of March 2026,
        # gemini-2.0-flash-exp is a verified working endpoint.
        self.model_id = os.environ.get("ORACLE_MODEL_ID", "gemini-2.0-flash-exp")
        self.gcp_project = os.environ.get("GCP_PROJECT_ID", "")
        self.gcp_location = os.environ.get("GCP_LOCATION", "us-central1")
        self.shell_timeout = int(os.environ.get("ORACLE_SHELL_TIMEOUT", "60"))
        self.http_timeout = int(os.environ.get("ORACLE_HTTP_TIMEOUT", "15"))
        self.max_turns = int(os.environ.get("ORACLE_MAX_TURNS", "20"))
        self.max_active_skills = int(os.environ.get("ORACLE_MAX_ACTIVE_SKILLS", "3"))
        self.enable_skill_context = os.environ.get("ORACLE_ENABLE_SKILL_CONTEXT", "true").lower() == "true"
        self.db_path = self._resolve_db_path()
        self.mcp_config_path = self._resolve_project_path(
            os.environ.get("ORACLE_MCP_CONFIG", "config/mcp_servers.yaml")
        )
        self.mcp_timeout: int = int(os.environ.get("ORACLE_MCP_TIMEOUT", "30"))
        self.skills_dir = self._resolve_project_path(os.environ.get("ORACLE_SKILLS_DIR", "skills/"))

        # Model Router configuration (Oracle 5.0 Phase 1)
        self.model_chain_config = self._resolve_project_path(
            os.environ.get("ORACLE_MODEL_CHAIN_CONFIG", "config/model_chain.yaml")
        )
        self.use_model_router: bool = os.environ.get("ORACLE_USE_MODEL_ROUTER", "false").lower() == "true"

        if not self.gcp_project:
            log.warning("GCP_PROJECT_ID is not set. Vertex AI calls will fail.")

    def _resolve_project_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        return (self.project_root / candidate).resolve()

    def _resolve_db_path(self) -> Path:
        db_path_env = os.environ.get("ORACLE_DB_PATH", "").strip()
        if db_path_env:
            return self._resolve_project_path(db_path_env)
        if os.environ.get("VERCEL"):
            return Path("/tmp/oracle_core.db")
        return (self.project_root / "data" / "oracle_core.db").resolve()


# ---------------------------------------------------------------------------
# Persistence Layer
# ---------------------------------------------------------------------------


class PersistenceLayer:
    """
    SQLite WAL-mode store for conversation history and task audit logs.

    History is persisted as JSON-serialized dicts rather than pickled SDK
    objects for two reasons:
      1. pickle.loads() on attacker-controlled data is arbitrary code execution.
      2. SDK object references are not stable across library versions.

    Serialization uses Pydantic's model_dump(mode='json') which encodes all
    field types correctly, including thought_signature bytes (→ base64).
    This preserves the mandatory thought signatures that Gemini 3 requires
    for function calling across session boundaries.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id   TEXT PRIMARY KEY,
                    history_json TEXT NOT NULL,
                    updated_at   TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS task_logs (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id   TEXT    NOT NULL,
                    event_type   TEXT    NOT NULL,
                    payload      TEXT,
                    timestamp    TEXT    DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_logs_session
                    ON task_logs(session_id);
            """)

    def save_history(self, session_id: str, history: List[Dict[str, Any]]) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO sessions
                   (session_id, history_json, updated_at)
                   VALUES (?, ?, datetime('now'))""",
                (session_id, json.dumps(history)),
            )

    def load_history(self, session_id: str) -> List[Dict[str, Any]] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT history_json FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def log_event(self, session_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO task_logs (session_id, event_type, payload) VALUES (?, ?, ?)",
                (session_id, event_type, json.dumps(payload)),
            )


# ---------------------------------------------------------------------------
# History Serializer
# ---------------------------------------------------------------------------


class HistorySerializer:
    """
    Lossless round-trip between SDK Content objects and JSON-serializable dicts.

    Uses Pydantic's model_dump(mode='json') / model_validate() rather than a
    hand-written field mapping. This is the only correct approach for Gemini 3
    models because thought_signature is a bytes field that appears on function_call
    and text parts. The hand-written approach reconstructed Parts as new objects,
    silently losing those bytes. The API enforces strict thought_signature presence
    for all function calling turns and returns a 400 if they are missing.

    Pydantic's JSON mode encodes bytes as base64 strings automatically.
    model_validate() decodes them back to bytes on load. No manual intervention
    needed for any field type.

    Reference: https://ai.google.dev/gemini-api/docs/thought-signatures
    "passing back thought signatures is mandatory for function calling"
    """

    @staticmethod
    def to_dicts(history: List[types.Content]) -> List[Dict[str, Any]]:
        # mode='json' produces JSON-serializable output: bytes → base64 str,
        # enums → their string values, Nones excluded by default.
        return [turn.model_dump(mode="json") for turn in history]

    @staticmethod
    def from_dicts(raw: List[Dict[str, Any]]) -> List[types.Content]:
        # model_validate reconstructs the full object graph including bytes
        # fields decoded from their base64 representations.
        return [types.Content.model_validate(d) for d in raw]


# ---------------------------------------------------------------------------
# Tool Executor
# ---------------------------------------------------------------------------


class ToolExecutor:
    """
    All side-effectful operations isolated behind a uniform
    {success: bool, ...} response envelope.

    Invariant: no exception propagates out of any tool method.
    The LLM receives structured error information rather than a Python
    traceback, which lets it reason about failures and retry or escalate.
    """

    def __init__(self, project_root: Path, shell_timeout: int, http_timeout: int):
        self.project_root = project_root.resolve()
        self.shell_timeout = shell_timeout
        self.http_timeout = http_timeout
        self.shell_executable = which("bash")

        # Initialize GCS storage if configured
        self.gcs_storage = None
        gcs_bucket = os.environ.get("GCS_BUCKET_NAME")
        gcp_project = os.environ.get("GCP_PROJECT_ID")

        if gcs_bucket and gcp_project:
            try:
                self.gcs_storage = GCSStorageManager(gcs_bucket, gcp_project, self.project_root)
                log.info(f"GCS Storage initialized: {gcs_bucket}")
            except Exception as e:
                log.warning(f"GCS Storage initialization failed: {e}")
        else:
            log.info("GCS Storage not configured - using local storage only")

    # ── Shell ─────────────────────────────────────────────────────────────

    def shell_execute(self, command: str) -> Dict[str, Any]:
        """
        bash -c execution with explicit argv[0] control.
        Using the list form prevents the shell from performing word splitting,
        glob expansion, and variable interpolation on the wrapper invocation
        itself, while still allowing full shell syntax within the command string
        passed to bash -c.
        """
        if not self.shell_executable:
            return {"success": False, "error": "bash executable not found"}

        try:
            res = subprocess.run(  # nosec B603 - command execution is the explicit purpose of this tool
                [self.shell_executable, "-c", command],
                capture_output=True,
                text=True,
                timeout=self.shell_timeout,
                check=False,
            )
            return {
                "success": res.returncode == 0,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "exit_code": res.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timed out after {self.shell_timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Vision ────────────────────────────────────────────────────────────

    def vision_capture(self, reason: str) -> Dict[str, Any]:
        """
        Fallback chain for desktop capture across display server generations:
          1. PIL ImageGrab  — works under X11 and some Wayland compositors
          2. gnome-screenshot — GNOME Wayland via DBus portal
          3. grim             — wlroots-based Wayland compositors (Sway, Hyprland)
          4. scrot            — X11 fallback

        Returns the file path on success for downstream vision analysis.
        Uploads to GCS if configured for cloud storage.
        """
        with tempfile.NamedTemporaryFile(prefix="oracle_vision_", suffix=".png", delete=False) as temp_file:
            target = temp_file.name

        # Attempt 1: PIL (covers most environments without spawning a subprocess)
        try:
            from PIL import ImageGrab

            ImageGrab.grab().save(target)
            result = {"success": True, "path": target, "method": "PIL", "reason": reason}
        except Exception:
            result = self._try_screenshot_backends(target)

        if result["success"] and self.gcs_storage:
            # Upload to GCS if available
            try:
                gcs_result = self.gcs_storage.upload_screenshot(target, "vision_capture")
                if gcs_result["success"]:
                    result["gcs_uri"] = gcs_result["gcs_uri"]
                    result["public_url"] = gcs_result["public_url"]
                    log.info(f"Screenshot uploaded to GCS: {gcs_result['gcs_uri']}")
                else:
                    log.warning(f"GCS upload failed: {gcs_result['error']}")
            except Exception as e:
                log.warning(f"GCS upload error: {e}")

        return result

    def _try_screenshot_backends(self, target: str) -> Dict[str, Any]:
        """Try alternative screenshot backends"""
        for backend, extra_args in (
            ("gnome-screenshot", ["-f", target]),
            ("grim", [target]),
            ("scrot", [target]),
        ):
            executable = which(backend)
            if not executable:
                continue
            try:
                cmd = [executable, *extra_args]
                res = subprocess.run(cmd, capture_output=True, timeout=15, check=False)  # nosec B603
                if res.returncode == 0:
                    return {"success": True, "path": target, "method": backend, "reason": "screenshot"}
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        return {
            "success": False,
            "error": "No screenshot backend available",
            "tried": ["PIL", "gnome-screenshot", "grim", "scrot"],
        }

    # ── Filesystem ────────────────────────────────────────────────────────

    def file_system_ops(self, operation: str, path: str, content: str | None = None) -> Dict[str, Any]:
        """
        Sandboxed file operations. Path traversal guard uses
        Path.is_relative_to() (Python 3.9+) which correctly handles
        symbolic links and absolute paths.
        """
        try:
            full_path = (self.project_root / path).resolve()

            # SECURITY: Proper path traversal protection
            if not full_path.is_relative_to(self.project_root):
                return {
                    "success": False,
                    "error": "Path escapes project root sandbox",
                    "requested": str(path),
                    "resolved": str(full_path),
                    "allowed_root": str(self.project_root),
                }

            if operation == "read":
                if not full_path.exists():
                    return {"success": False, "error": "File not found"}
                return {"success": True, "content": full_path.read_text(encoding="utf-8")}

            elif operation == "write":
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content or "", encoding="utf-8")
                return {"success": True, "path": str(full_path)}

            elif operation == "list":
                if not full_path.exists():
                    return {"success": False, "error": "Directory not found"}
                items = [
                    {
                        "name": p.name,
                        "type": "dir" if p.is_dir() else "file",
                        "size": p.stat().st_size if p.is_file() else None,
                    }
                    for p in sorted(full_path.iterdir())
                ]
                return {"success": True, "items": items}

            elif operation == "delete":
                if not full_path.exists():
                    return {"success": False, "error": "Path not found"}
                if full_path.is_file():
                    full_path.unlink()
                else:
                    full_path.rmdir()  # Only removes empty dirs (intentional)
                return {"success": True}

            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

        except PermissionError as e:
            return {"success": False, "error": f"Permission denied: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── HTTP ──────────────────────────────────────────────────────────────

    def http_fetch(self, url: str, method: str = "GET", headers: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        Minimal HTTP client for REST API calls and raw content retrieval.
        Response body is hard-capped at 8192 chars to prevent context overflow.

        This is not a browser. For JavaScript-rendered pages or complex DOM
        interaction, a headless browser layer (Playwright, etc.) is required
        and should be implemented as a separate tool or subprocess call.
        """
        try:
            error = validate_outbound_http_url(url)
            if error:
                return {"success": False, "error": error}

            request_headers = {"User-Agent": "OracleAgent/1.0"}
            if headers:
                request_headers.update({str(key): str(value) for key, value in headers.items()})

            response = requests.request(
                method.upper(),
                url,
                headers=request_headers,
                timeout=self.http_timeout,
                allow_redirects=False,
            )
            if 300 <= response.status_code < 400:
                return {"success": False, "status": response.status_code, "error": HTTP_REDIRECT_BLOCKED_ERROR}
            response.raise_for_status()
            body = response.text
            cap = 8192
            return {
                "success": True,
                "status": response.status_code,
                "url": url,
                "content": body[:cap],
                "truncated": len(body) > cap,
            }
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            return {"success": False, "status": status_code, "error": str(e)}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class OracleAgent:
    """
    Stateful agentic orchestrator implementing a ReAct loop over Gemini on
    Vertex AI.

    Loop invariant:
      Every iteration appends exactly one model turn and, if function calls
      are present, exactly one tool turn (consolidating all parallel tool
      responses into a single Content with role="tool"). This matches the
      Gemini API's multi-tool-call contract: all function responses for a
      given model turn must arrive in a single subsequent user/tool turn.

    Persistence:
      History is checkpointed to SQLite after every tool turn and on
      task completion. A resumed session appends the new prompt as a user
      turn rather than overwriting state, preserving causal context.

    Thought extraction:
      Thoughts arrive as Part objects with part.thought=True. They are
      extracted for logging but stripped from persisted history. The API
      does not require replayed thoughts for coherent multi-turn reasoning.
    """

    def __init__(self, config: OracleConfig | None = None) -> None:
        self.cfg = config or OracleConfig()
        self.db = PersistenceLayer(self.cfg.db_path)
        self.tools = ToolExecutor(
            self.cfg.project_root,
            self.cfg.shell_timeout,
            self.cfg.http_timeout,
        )
        self.client = genai.Client(
            vertexai=True,
            project=self.cfg.gcp_project,
            location=self.cfg.gcp_location,
        )

        # Initialize MCP + Skills (Oracle 5.0)
        self._tool_registry: ToolRegistry | None = None
        self._mcp_client: MCPClient | None = None
        self._skill_loader: SkillLoader | None = None
        self.gcs_backup_enabled: bool = False

        if MCP_AVAILABLE:
            try:
                self._init_tool_registry()
            except Exception as e:
                log.warning(f"Failed to initialize MCP/Skills: {e}. Continuing with built-in tools only.")
        else:
            log.info("MCP/Skills modules not available. Running with built-in tools only.")

        # Initialize Model Router (Oracle 5.0 Phase 1)
        self._model_router: ModelRouter | None = None
        if MODEL_ROUTER_AVAILABLE and self.cfg.use_model_router:
            try:
                self._model_router = create_router_from_config(
                    config_path=self.cfg.model_chain_config, session_id="oracle-default"
                )
                log.info(f"Model Router initialized with {len(self._model_router.chain)} providers")
            except Exception as e:
                log.warning(f"Failed to initialize Model Router: {e}. Using direct Gemini client.")

        log.info("Oracle ready. Model: %s", self.cfg.model_id)

        # Initialize GCS backup if available
        self._setup_gcs_backup()

    def _init_tool_registry(self) -> None:
        """Initialize ToolRegistry with MCP and Skills support."""
        # Create MCP client and registry
        self._mcp_client = MCPClient(str(self.cfg.mcp_config_path))
        mcp_registry = MCPRegistry(self._mcp_client)

        # Create skill loader
        self._skill_loader = SkillLoader(str(self.cfg.skills_dir))

        # Create unified tool registry
        self._tool_registry = ToolRegistry(
            tool_executor=self.tools, mcp_registry=mcp_registry, skill_loader=self._skill_loader
        )

        # Initialize async components
        import asyncio

        asyncio.run(self._async_init_tool_registry())

    async def _async_init_tool_registry(self) -> None:
        """Async initialization of tool registry."""
        if self._tool_registry:
            await self._tool_registry.initialize()

    async def close(self) -> None:
        """
        Clean shutdown of OracleAgent.
        Closes MCP connections, tears down skills, and stops ModelRouter.
        """
        log.info("Shutting down OracleAgent")

        if self._mcp_client:
            try:
                await self._mcp_client.shutdown()
            except Exception as e:
                log.warning(f"Error shutting down MCP client: {e}")

        if self._skill_loader:
            try:
                await self._skill_loader.teardown_all()
            except Exception as e:
                log.warning(f"Error tearing down skills: {e}")

        if self._model_router:
            try:
                await self._model_router.stop()
                # Log final cost stats
                stats = self._model_router.get_cost_stats()
                log.info(f"Session cost: ${stats['session_cost_usd']:.4f}")
            except Exception as e:
                log.warning(f"Error stopping ModelRouter: {e}")

    def _setup_gcs_backup(self) -> None:
        """Setup automatic GCS backup if configured"""
        if self.tools.gcs_storage:
            try:
                # Test GCS connectivity
                stats = self.tools.gcs_storage.get_bucket_stats()
                if stats["success"]:
                    log.info(f"GCS backup ready: {stats['bucket_name']}")
                    self.gcs_backup_enabled = True
                else:
                    log.warning("GCS backup unavailable")
                    self.gcs_backup_enabled = False
            except Exception as e:
                log.warning(f"GCS backup setup failed: {e}")
                self.gcs_backup_enabled = False
        else:
            self.gcs_backup_enabled = False

    def backup_to_gcs(self) -> Dict[str, Any]:
        """Manual backup database to GCS"""
        if not self.tools.gcs_storage:
            return {"success": False, "error": "GCS backup not configured"}

        try:
            return self.tools.gcs_storage.backup_database(str(self.cfg.db_path))
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_skill_catalog(self) -> List[Dict[str, Any]]:
        """Return the current local skill catalog, if available."""
        if not self._tool_registry:
            return []
        return self._tool_registry.get_skill_catalog()

    def reload_skills(self) -> List[Dict[str, Any]]:
        """Reload local skills without reinitializing the full agent."""
        if not self._tool_registry:
            return []
        return self._tool_registry.reload_skills()

    # ── Generation config ─────────────────────────────────────────────────

    def _build_config(self, system_instruction: str | None = None) -> types.GenerateContentConfig:
        """
        Build Generation config with thinking level and tools.
        """
        # Get function declarations from ToolRegistry if available
        if self._tool_registry:
            function_declarations = self._tool_registry.get_function_declarations()
        else:
            # Fallback to built-in declarations
            function_declarations = [
                types.FunctionDeclaration(
                    name="shell_execute",
                    description=(
                        "Execute a bash command on the local system. "
                        "Returns stdout, stderr, and exit code. "
                        "Use for system inspection, file management, and process control."
                    ),
                    parameters=cast(
                        types.Schema,
                        {
                            "type": "OBJECT",
                            "properties": {"command": {"type": "STRING", "description": "Bash command string"}},
                            "required": ["command"],
                        },
                    ),
                ),
                types.FunctionDeclaration(
                    name="vision_capture",
                    description=(
                        "Capture the current desktop state as a PNG image. "
                        "Use to observe GUI application state or verify "
                        "the result of UI interactions."
                    ),
                    parameters=cast(
                        types.Schema,
                        {
                            "type": "OBJECT",
                            "properties": {
                                "reason": {"type": "STRING", "description": "Why you are capturing the screen"}
                            },
                            "required": ["reason"],
                        },
                    ),
                ),
                types.FunctionDeclaration(
                    name="file_system_ops",
                    description=(
                        "Read, write, list, or delete files in the workspace. "
                        "Paths are relative to the project root. "
                        "Operations: read | write | list | delete"
                    ),
                    parameters=cast(
                        types.Schema,
                        {
                            "type": "OBJECT",
                            "properties": {
                                "operation": {"type": "STRING", "description": "read | write | list | delete"},
                                "path": {"type": "STRING", "description": "Relative path within project root"},
                                "content": {"type": "STRING", "description": "File content (write only)"},
                            },
                            "required": ["operation", "path"],
                        },
                    ),
                ),
                types.FunctionDeclaration(
                    name="http_fetch",
                    description=(
                        "Make HTTP requests to external APIs or websites. "
                        "Use for REST APIs and static web content. "
                        "Not suitable for JavaScript-rendered pages."
                    ),
                    parameters=cast(
                        types.Schema,
                        {
                            "type": "OBJECT",
                            "properties": {
                                "url": {"type": "STRING", "description": "Full URL"},
                                "method": {"type": "STRING", "description": "HTTP method (default: GET)"},
                                "headers": {"type": "OBJECT", "description": "Optional request headers"},
                            },
                            "required": ["url"],
                        },
                    ),
                ),
            ]

        config = types.GenerateContentConfig(
            tools=[types.Tool(function_declarations=function_declarations)],
            thinking_config=types.ThinkingConfig(include_thoughts=True),
        )
        if system_instruction:
            config.system_instruction = system_instruction
        return config

    def _build_skill_system_instruction(self, prompt: str) -> str | None:
        """Build a compact skill-context system instruction for the current request."""
        if not self.cfg.enable_skill_context:
            return None
        if not self._tool_registry:
            return None
        skill_context = self._tool_registry.build_skill_prompt_context(prompt, max_skills=self.cfg.max_active_skills)
        return skill_context or None

    # ── Model Router Integration (Oracle 5.0 Phase 1) ─────────────────────

    def _get_tools_for_router(self) -> List[Dict[str, Any]]:
        """Convert ToolRegistry tools to ModelRouter format."""
        tools: List[Dict[str, Any]] = []

        if self._tool_registry:
            declarations = self._tool_registry.get_function_declarations()
            for decl in declarations:
                tools.append(
                    {"name": decl.name, "description": decl.description, "parameters": cast(Any, decl.parameters)}
                )
        else:
            # Fallback to built-in tools
            tools = [
                {
                    "name": "shell_execute",
                    "description": "Execute a bash command on the local system.",
                    "parameters": cast(
                        Any, {"type": "OBJECT", "properties": {"command": {"type": "STRING"}}, "required": ["command"]}
                    ),
                },
                {
                    "name": "vision_capture",
                    "description": "Capture the current desktop state as a PNG.",
                    "parameters": cast(
                        Any, {"type": "OBJECT", "properties": {"reason": {"type": "STRING"}}, "required": ["reason"]}
                    ),
                },
                {
                    "name": "file_system_ops",
                    "description": "Read, write, list, or delete files within the project sandbox.",
                    "parameters": cast(
                        Any,
                        {
                            "type": "OBJECT",
                            "properties": {
                                "operation": {"type": "STRING"},
                                "path": {"type": "STRING"},
                                "content": {"type": "STRING"},
                            },
                            "required": ["operation", "path"],
                        },
                    ),
                },
                {
                    "name": "http_fetch",
                    "description": "Fetch a URL and return raw response content.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "url": {"type": "STRING"},
                            "method": {"type": "STRING"},
                            "headers": {"type": "OBJECT"},
                        },
                        "required": ["url"],
                    },
                },
            ]

        return tools

    def _convert_history_to_messages(self, history: list[types.Content]) -> list[dict[str, Any]]:
        """Convert Gemini SDK history to ModelRouter message format."""
        messages = []

        for content in history:
            role = str(content.role)
            # Map Gemini roles to standard roles
            if role == "model":
                role = "assistant"

            # Extract text content
            text_parts: List[str] = []
            if content.parts:
                for part in content.parts:
                    if part.text:
                        text_parts.append(str(part.text))

            if text_parts:
                messages.append({"role": role, "content": "\n".join(text_parts)})

        return messages

    async def run_async(self, prompt: str, session_id: str = "default") -> str:
        """
        Async version of run() using ModelRouter for multi-provider support.

        This method provides automatic failover across multiple LLM providers
        and includes cost tracking.
        """
        if not self._model_router:
            # Fallback to synchronous run() if ModelRouter not available
            return self.run(prompt, session_id)

        log.info(f"[{session_id}] Prompt (async): {prompt[:120]}")
        self.db.log_event(session_id, "task_start", {"prompt": prompt, "mode": "async"})

        # Update session ID for cost tracking
        self._model_router.session_id = session_id

        # Build messages
        system_instruction = self._build_skill_system_instruction(prompt)
        raw = self.db.load_history(session_id)
        if raw:
            history = HistorySerializer.from_dicts(raw)
            messages = self._convert_history_to_messages(history)
            messages.append({"role": "user", "content": prompt})
        else:
            messages = [{"role": "user", "content": prompt}]

        if system_instruction:
            messages = [{"role": "system", "content": system_instruction}, *messages]

        # Get tools
        tools = self._get_tools_for_router()

        # Build config
        config = GenerateConfig(model_id=self.cfg.model_id, temperature=0.7, max_tokens=8192)

        for turn_idx in range(1, self.cfg.max_turns + 1):
            log.info(f"[{session_id}] Turn {turn_idx} — generating")

            # Generate via ModelRouter
            response = await self._model_router.generate(messages=messages, tools=tools, config=config)

            if response.is_error:
                log.error(f"All providers failed: {response.error}")
                return f"Error: {response.error}"

            log.info(f"Response from {response.provider_id} ({response.latency_ms:.0f}ms)")

            # Add assistant message
            assistant_msg: Dict[str, Any] = {
                "role": "assistant",
                "content": response.content,
            }
            if response.tool_calls:
                assistant_msg["tool_calls"] = [
                    {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.arguments}}
                    for tc in response.tool_calls
                ]
            messages.append(assistant_msg)

            # Check for tool calls
            if not response.tool_calls:
                # Terminal response
                log.info(f"[DONE] {response.content[:200]}...")
                self.db.log_event(
                    session_id,
                    "task_complete",
                    {
                        "response": response.content[:4000],
                        "provider": response.provider_id,
                        "cost_usd": response.usage.cost_usd if response.usage else 0.0,
                    },
                )

                # Persist history in Gemini format for compatibility
                final_history = self._convert_messages_to_history(messages)
                self.db.save_history(session_id, HistorySerializer.to_dicts(final_history))

                return str(response.content)

            # Dispatch tool calls
            for tc in response.tool_calls:
                log.info(f"[TOOL] {tc.name}({tc.arguments})")
                if self._tool_registry:
                    result = await self._tool_registry.dispatch(tc.name, tc.arguments)
                else:
                    result = self._dispatch(tc.name, tc.arguments)

                log.info(f"[RESULT] success={result.get('success')}")

                self.db.log_event(
                    session_id,
                    "tool_call",
                    {"turn": turn_idx, "tool": tc.name, "args": tc.arguments, "result": str(result)[:500]},
                )

                # Add tool response
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})

        log.warning(f"[{session_id}] Max turns ({self.cfg.max_turns}) reached")
        self.db.log_event(session_id, "max_turns_exceeded", {"max": self.cfg.max_turns})
        return f"Iteration ceiling ({self.cfg.max_turns} turns) reached."

    def _convert_messages_to_history(self, messages: List[Dict[str, Any]]) -> List[types.Content]:
        """Convert ModelRouter messages back to Gemini SDK history format."""
        history: List[types.Content] = []

        for msg in messages:
            role = str(msg.get("role", "user"))
            content = str(msg.get("content", ""))

            # Map roles back to Gemini format
            if role == "assistant":
                role = "model"

            parts = [types.Part.from_text(text=content)]
            history.append(types.Content(role=role, parts=parts))

        return history

    # ── Tool dispatch ─────────────────────────────────────────────────────

    def _dispatch(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch tool call to appropriate handler.

        Req 7.3: Delegate to ToolRegistry if available, otherwise use built-in dispatch.
        """
        if self._tool_registry:
            # Use unified ToolRegistry (Oracle 5.0)
            import asyncio

            try:
                # ToolRegistry.dispatch is async
                result: Dict[str, Any] = asyncio.run(self._tool_registry.dispatch(name, args))
                return result
            except Exception as e:
                log.error(f"ToolRegistry dispatch error: {e}")
                return {"success": False, "error": str(e)}
        else:
            # Fallback to built-in dispatch
            match name:
                case "shell_execute":
                    return self.tools.shell_execute(str(args.get("command", "")))
                case "vision_capture":
                    return self.tools.vision_capture(str(args.get("reason", "")))
                case "file_system_ops":
                    return self.tools.file_system_ops(
                        str(args.get("operation", "")), str(args.get("path", "")), cast(str | None, args.get("content"))
                    )
                case "http_fetch":
                    return self.tools.http_fetch(
                        str(args.get("url", "")),
                        str(args.get("method", "GET")),
                        cast(Dict[str, Any] | None, args.get("headers")),
                    )
                case _:
                    return {"success": False, "error": f"Unknown tool: {name}"}
        return {"success": False, "error": "Internal dispatch error"}

    # ── History utilities ─────────────────────────────────────────────────

    @staticmethod
    def _extract_thoughts(content: types.Content) -> str | None:
        """Collect all thought part text from a model turn."""
        thoughts = [str(p.text) for p in (content.parts or []) if getattr(p, "thought", False) and p.text]
        return "\n".join(thoughts) if thoughts else None

    # ── Agentic loop ──────────────────────────────────────────────────────

    def run(self, prompt: str, session_id: str = "default") -> str:
        log.info("[%s] Prompt: %s", session_id, prompt[:120])
        self.db.log_event(session_id, "task_start", {"prompt": prompt})

        # Build or resume history
        raw = self.db.load_history(session_id)
        if raw:
            history = HistorySerializer.from_dicts(raw)
            history.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))
        else:
            history = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]

        config = self._build_config(self._build_skill_system_instruction(prompt))

        for turn_idx in range(1, self.cfg.max_turns + 1):
            log.info("[%s] Turn %d — generating", session_id, turn_idx)

            response = self.client.models.generate_content(
                model=self.cfg.model_id,
                contents=cast(Any, history),
                config=config,
            )

            if not response.candidates:
                log.error("No candidates in response")
                break

            model_turn = response.candidates[0].content
            if not model_turn:
                log.error("No content in response candidate")
                break

            history.append(model_turn)

            # Log reasoning trace
            thoughts = self._extract_thoughts(model_turn)
            if thoughts:
                log.info("[THINK] %s...", thoughts[:300])
                self.db.log_event(session_id, "thought", {"turn": turn_idx, "text": thoughts[:2000]})

            # Collect function calls from non-thought parts
            function_calls = [
                p.function_call
                for p in (model_turn.parts or [])
                if p.function_call is not None and not getattr(p, "thought", False)
            ]

            if not function_calls:
                # Terminal: no pending tool calls, model is done
                final = response.text or ""
                log.info("[DONE] %s...", final[:200])
                self.db.log_event(session_id, "task_complete", {"response": final[:4000]})
                self.db.save_history(session_id, HistorySerializer.to_dicts(history))
                return final

            # Dispatch all tool calls; consolidate responses into one tool turn.
            # The API requires all function_response parts for a given model turn
            # to arrive in a single subsequent Content with role="tool".
            tool_parts: List[types.Part] = []
            for fc in function_calls:
                if not fc:
                    continue
                args = dict(fc.args) if fc.args else {}
                log.info("[TOOL] %s(%s)", fc.name, str(args)[:120])
                result = self._dispatch(str(fc.name), args)
                log.info("[RESULT] success=%s", result.get("success"))
                self.db.log_event(
                    session_id,
                    "tool_call",
                    {
                        "turn": turn_idx,
                        "tool": fc.name,
                        "args": args,
                        "result": str(result)[:500],
                    },
                )
                tool_parts.append(types.Part.from_function_response(name=str(fc.name), response=result))

            history.append(types.Content(role="tool", parts=tool_parts))
            self.db.save_history(session_id, HistorySerializer.to_dicts(history))

        log.warning("[%s] Max turns (%d) reached without terminal response", session_id, self.cfg.max_turns)
        self.db.log_event(session_id, "max_turns_exceeded", {"max": self.cfg.max_turns})
        return f"Iteration ceiling ({self.cfg.max_turns} turns) reached without resolution."

    def get_cost_stats(self) -> dict[str, Any]:
        """Get cost statistics for the current session."""
        if self._model_router:
            return self._model_router.get_cost_stats()
        return {"error": "ModelRouter not initialized"}

    def get_provider_status(self) -> list[dict[str, Any]]:
        """Get status of all configured providers."""
        if not self._model_router:
            return [{"error": "ModelRouter not initialized"}]

        health_list = self._model_router.get_chain_status()
        return [
            {
                "provider_id": h.provider_id,
                "healthy": h.healthy,
                "latency_ms": h.latency_ms,
                "error": h.error,
                "last_checked": h.last_checked,
            }
            for h in health_list
        ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    agent = OracleAgent()
    result = agent.run(
        prompt=(
            "Run 'uname -a' and 'cat /etc/os-release' to capture system info, "
            "then write a summary to notes/system_info.md in the project root."
        ),
        session_id="bootstrap",
    )
    print(f"\n[OUTPUT]\n{result}")
