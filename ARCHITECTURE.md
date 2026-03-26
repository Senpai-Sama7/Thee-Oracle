# Oracle Agent System Architecture
> **Status:** Historical broad architecture reference. Cross-check current behavior against `README.md` and `AGENTS.md`.

This document provides a broad architectural representation of the Oracle Agent orchestration system, including earlier v1/v2 migration concepts. It is useful for context, but it is not the source of truth for the current maintained runtime.

## System Architecture Diagram

```mermaid
graph TD
    %% Styling Definitions
    classDef client fill:#2C3E50,stroke:#FFF,stroke-width:2px,color:#FFF;
    classDef orchestrator fill:#34495E,stroke:#3498DB,stroke-width:2px,color:#FFF;
    classDef agent fill:#8E44AD,stroke:#2980B9,stroke-width:2px,color:#FFF;
    classDef tool fill:#27AE60,stroke:#2ECC71,stroke-width:2px,color:#FFF;
    classDef data fill:#E67E22,stroke:#D35400,stroke-width:2px,color:#FFF;
    classDef cloud fill:#2980B9,stroke:#3498DB,stroke-width:2px,color:#FFF;
    classDef external fill:#16A085,stroke:#1ABC9C,stroke-width:2px,color:#FFF;
    classDef queue fill:#C0392B,stroke:#E67E22,stroke-width:2px,color:#FFF;

    %% Entry Points
    subgraph "Entry Points & Interfaces"
        CLI[main.py / demo.py]:::client
        HC[health_check.py :8080]:::client
    end

    %% Core Orchestration Layer
    subgraph "Orchestration Layer (orchestrator.py)"
        WC[WorkflowController]:::orchestrator
        TS[TaskStore / ResultStore]:::data
        SCH[RecurringScheduler]:::orchestrator
        CB[CircuitBreaker]:::orchestrator
        RL[AsyncTokenBucket]:::orchestrator
        MR[MetricsRegistry]:::orchestrator
        
        WC --> TS
        WC --> SCH
        WC --> CB
        WC --> RL
        WC --> MR
    end

    %% Oracle Agent System
    subgraph "Oracle Agent Core (src/oracle/agent_system.py)"
        OA[OracleAgent]:::agent
        OC[OracleConfig]:::agent
        
        %% Model & Execution
        GENAI[genai.Client<br>Gemini 2.0 Flash]:::cloud
        TE[ToolExecutor]:::tool
        
        %% Persistence & Memory
        PL[PersistenceLayer]:::data
        HS[HistorySerializer]:::data
        
        OA --> OC
        OA --> GENAI
        OA --> TE
        OA --> PL
        PL --> HS
    end

    %% Tool Ecosystem
    subgraph "Sandboxed Tool Surface"
        SH[shell_execute<br>['bash', '-c']]:::tool
        FS[file_system_ops<br>read/write/list]:::tool
        VC[vision_capture<br>PIL/gnome/scrot]:::tool
        HTTP[http_fetch<br>8192 char limit]:::tool
        GCS[GCSStorageManager<br>gcs_storage.py]:::cloud
        
        TE --> SH
        TE --> FS
        TE --> VC
        TE --> HTTP
        TE --> GCS
    end

    %% Distributed Knowledge & Async Workers
    subgraph "Distributed Async Workers"
        KW[knowledge_worker.py]:::agent
        RMQ[(RabbitMQ<br>Task Queue)]:::queue
        DE[Discovery Engine API]:::cloud
        
        RMQ <--> KW
        KW --> DE
    end

    %% Infrastructure & Storage
    subgraph "Data & Persistence"
        SQL[(SQLite WAL<br>oracle_core.db)]:::data
        PG[(PostgreSQL<br>Production)]:::data
        BUCKET[(Google Cloud Storage<br>Screenshots/Backups)]:::cloud
        
        PL --> SQL
        PL -.-> PG
        GCS --> BUCKET
    end

    %% Connections & Flow
    CLI --> WC
    WC --> OA
    OA --> RMQ
    HC --> MR
    HC --> SQL

    %% Tool Effects
    SH -.-> FS
    VC -.-> FS
    VC --> GCS
```

## Component Interconnectivity & Invariants

### 1. ReAct Loop Execution (OracleAgent)
- **Initialization:** Reads configuration via `OracleConfig` mapping to `.env`.
- **Memory Loading:** Retrieves past conversations via `PersistenceLayer` using the `HistorySerializer` (which enforces **Pydantic JSON** over insecure Pickle).
- **Inference:** Calls `genai.Client.models.generate_content()` with available tool schemas.
- **Dispatch:** Tools are triggered through `_dispatch()`. Responses are rigorously enforced into a single consolidated `Content(role="tool")` turn before the loop repeats (Max defaults to 20 turns).

### 2. Tool Execution Envelope
All tools (`shell_execute`, `vision_capture`, `file_system_ops`, `http_fetch`) execute within a highly restricted `ToolExecutor` sandbox.
- Exceptions never leak; all tools return a structured dictionary: `{"success": bool, "result": any, "error": str}`.
- Shell commands strictly use `["bash", "-c", cmd]` to prevent shell injection vectors.
- Filesystem bounds are strictly constrained to `project_root`.

### 3. Asynchronous Distribution
The `knowledge_worker.py` acts as an independent process connecting to **RabbitMQ**, designed for heavy retrieval tasks (e.g., Google Discovery Engine). It utilizes exponential backoff, circuit breaking, and poison-pill message rejection without blocking the main event loop.

### 4. V2 Preparation (Ralph Agent Routing)
As the system transitions to V2, `OracleAgent` serves as the primary router, decoupling the "Knowledge/Embedding Phase" from the "Browser Automation Phase", feeding into specialized sub-agents based on the model-agnostic routing specifications defined in `.kiro/specs/oracle-platform-v2`.

---
*Generated based on rigorous analysis of `AGENTS.md`, `CLAUDE.md`, and system directory structures.*
