# Oracle 5.0 - Implementation Guide
## Developer Onboarding & Sprint Planning

---

## Quick Start for Developers

### Prerequisites

```bash
# Required
python >= 3.11
node >= 20

# Optional but recommended
docker >= 24.0
ollama (for local models)
git >= 2.40
```

### Development Setup

```bash
# Clone repository
git clone https://github.com/oracle-ai/oracle.git
cd oracle

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install Node dependencies for Dev UI
cd dev-ui && npm install && cd ..

# Copy example configuration
cp config/oraclesettings.example.json ~/.oracle/oraclesettings.json

# Edit configuration
nano ~/.oracle/oraclesettings.json

# Run tests
pytest tests/ -v

# Start development server
oracle dev --all
```

---

## Sprint Planning

### Sprint 1: Foundation (2 weeks)

**Theme:** Core infrastructure

#### Week 1 Tasks

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 1 | Set up project structure | @lead | `src/oracle/v5/` structure |
| 1-2 | LLM Provider Interface | @backend | Abstract base class + Gemini impl |
| 2-3 | Anthropic Provider | @backend | Claude integration with tools |
| 3-4 | OpenAI Provider | @backend | GPT-4o integration |
| 4-5 | LLM Router with failover | @backend | Routing + cost tracking |

#### Week 2 Tasks

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 6 | Gateway service scaffold | @backend | FastAPI app structure |
| 6-7 | WebSocket handler | @backend | Bidirectional messaging |
| 7-8 | Session management | @backend | Isolated sessions |
| 8-9 | WhatsApp channel | @integrations | Baileys bridge |
| 9-10 | Telegram channel | @integrations | aiogram bot |

**Sprint 1 Definition of Done:**
- [ ] 3+ LLM providers working
- [ ] Failover tested
- [ ] WebSocket gateway accepting connections
- [ ] WhatsApp messages received and responded
- [ ] All tests passing

---

### Sprint 2: Multi-Agent (2 weeks)

**Theme:** Agent orchestration

#### Week 3 Tasks

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 11 | Agent base class | @backend | ReAct loop implementation |
| 11-12 | Tool execution framework | @backend | Tool registry + execution |
| 12-13 | Crew Manager scaffold | @backend | Workflow orchestrator |
| 13-14 | Hierarchical workflow | @backend | Planner → Workers → Synthesizer |
| 14-15 | Parallel execution | @backend | Async task coordination |

#### Week 4 Tasks

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 16 | Conditional branching | @backend | If/else in workflows |
| 16-17 | Agent YAML config | @backend | Crew configuration files |
| 17-18 | Markdown persistence | @backend | File-based storage |
| 18-19 | Git integration | @backend | Auto-commit on changes |
| 19-20 | End-to-end testing | @qa | Full workflow tests |

**Sprint 2 Definition of Done:**
- [ ] 3+ agents collaborating
- [ ] Complex workflow executes end-to-end
- [ ] Configuration in YAML/Markdown
- [ ] Sessions persist to files
- [ ] Git versioning works

---

### Sprint 3: User Interfaces (2 weeks)

**Theme:** TUI, GUI, Dev UI

#### Week 5 Tasks

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 21 | TUI scaffold | @frontend | Textual app structure |
| 21-22 | Chat view | @frontend | Message display |
| 22-23 | Input handling | @frontend | Message sending |
| 23-24 | Split panes | @frontend | Chat + Logs + Metrics |
| 24-25 | Streaming display | @frontend | Real-time token display |

#### Week 6 Tasks

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 26 | Dev UI scaffold | @frontend | React + Vite setup |
| 26-27 | Workflow designer | @frontend | ReactFlow canvas |
| 27-28 | Agent nodes | @frontend | Draggable agent components |
| 28-29 | Debugger panel | @frontend | Execution trace view |
| 29-30 | GUI scaffold (PyQt6) | @frontend | Desktop app window |

**Sprint 3 Definition of Done:**
- [ ] TUI functional with streaming
- [ ] Dev UI shows workflow designer
- [ ] GUI window opens
- [ ] All interfaces connect to Gateway

---

### Sprint 4: Protocols & Ecosystem (2 weeks)

**Theme:** MCP, A2A, Skills

#### Week 7 Tasks

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 31 | MCP client | @backend | Server connection |
| 31-32 | Tool discovery | @backend | List MCP tools |
| 32-33 | Tool execution | @backend | Call MCP tools |
| 33-34 | A2A server | @backend | Agent card endpoint |
| 34-35 | A2A client | @backend | Send/receive tasks |

#### Week 8 Tasks

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 36 | Skill format spec | @backend | YAML schema |
| 36-37 | Skill runtime | @backend | Execute skills |
| 37-38 | Skill sandbox | @backend | Permission enforcement |
| 38-39 | Marketplace client | @backend | Hub API integration |
| 39-40 | Auto-install | @backend | Search + install skills |

**Sprint 4 Definition of Done:**
- [ ] MCP tools execute
- [ ] A2A agents communicate
- [ ] Skill installs from hub
- [ ] Sandboxed execution works

---

### Sprint 5: Advanced Features (2 weeks)

**Theme:** Vector memory, CDP, heartbeat

#### Week 9 Tasks

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 41 | ChromaDB setup | @backend | Vector store |
| 41-42 | Embedding generation | @backend | Text to vectors |
| 42-43 | Semantic memory | @backend | Remember/recall |
| 43-44 | CDP browser launch | @backend | Playwright integration |
| 44-45 | Browser actions | @backend | Click, type, screenshot |

#### Week 10 Tasks

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 46 | Heartbeat scheduler | @backend | APScheduler setup |
| 46-47 | Task checking | @backend | Checklist execution |
| 47-48 | Quiet hours | @backend | Time-based pausing |
| 48-49 | iOS node scaffold | @mobile | SwiftUI app |
| 49-50 | Android node scaffold | @mobile | Jetpack Compose app |

**Sprint 5 Definition of Done:**
- [ ] Semantic search works
- [ ] Browser control functional
- [ ] Heartbeat sends notifications
- [ ] Mobile apps connect

---

### Sprint 6: Polish & Release (2 weeks)

**Theme:** Testing, documentation, release

#### Week 11-12 Tasks

- Performance optimization
- Security audit
- Documentation
- Example configurations
- Migration guide
- Release candidates

---

## Development Workflows

### Branch Strategy

```
main
├── develop
│   ├── feature/llm-router
│   ├── feature/gateway
│   ├── feature/crew-manager
│   ├── feature/tui
│   └── ...
├── hotfix/security-patch
└── release/v5.0.0
```

### Commit Convention

```
type(scope): subject

body

footer
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance

Examples:
```
feat(llm): add Anthropic provider with tool support

Implements Claude 3.5 Sonnet integration with native
tool calling and streaming support.

Closes #123
```

### Testing Strategy

```python
# Unit test example
def test_llm_router_failover():
    router = LLMRouter()
    
    # Register providers
    router.register_provider("primary", MockFailingProvider())
    router.register_provider("fallback", MockWorkingProvider())
    
    # Test failover
    response = router.generate([message])
    
    assert response.provider == "fallback"

# Integration test example
@pytest.mark.asyncio
async def test_whatsapp_e2e():
    gateway = GatewayServer(test_config)
    await gateway.startup()
    
    # Send test message
    message = create_test_message("Hello")
    response = await gateway.route_message(message)
    
    assert "hello" in response.content.lower()
    
    await gateway.shutdown()
```

### Code Review Checklist

- [ ] Tests pass
- [ ] Type hints complete
- [ ] Documentation updated
- [ ] No security vulnerabilities
- [ ] Performance acceptable
- [ ] Backwards compatibility (if applicable)

---

## Debugging

### Enable Debug Logging

```bash
export ORACLE_LOG_LEVEL=DEBUG
export ORACLE_LOG_FORMAT=detailed
oracle start
```

### Inspect Sessions

```bash
# List active sessions
oracle sessions list

# View session history
oracle sessions show <session_id>

# Export session
oracle sessions export <session_id> --format markdown
```

### Monitor Gateway

```bash
# WebSocket debug
curl http://localhost:18789/health

# Metrics
oracle metrics --realtime

# Logs tail
oracle logs --follow --level DEBUG
```

### Dev UI Debug Mode

```bash
cd dev-ui
npm run dev  # Starts with hot reload
```

---

## Deployment

### Local Development

```bash
# All services
oracle start --all

# Specific services
oracle start --tui --gateway

# With hot reload
oracle dev --watch
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  oracle:
    build: .
    ports:
      - "18789:18789"
      - "8080:8080"
    volumes:
      - ~/.oracle:/home/oracle/.oracle
    environment:
      - ORACLE_MODE=personal
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      
  chroma:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma
      
volumes:
  chroma_data:
```

### Production Checklist

- [ ] SSL certificates configured
- [ ] API keys rotated
- [ ] Rate limiting enabled
- [ ] Audit logging active
- [ ] Health checks configured
- [ ] Backups scheduled
- [ ] Monitoring dashboards
- [ ] Incident response plan

---

## Troubleshooting

### Common Issues

**Gateway won't start:**
```bash
# Check port availability
lsof -i :18789

# Check configuration
oracle config validate

# View logs
oracle logs --service gateway
```

**LLM provider failing:**
```bash
# Test provider
oracle llm test --provider anthropic

# Check API key
echo $ANTHROPIC_API_KEY | head -c 10

# View router status
oracle llm status
```

**Messaging not working:**
```bash
# Check channel status
oracle channels status

# Reauthenticate WhatsApp
oracle channels reconnect whatsapp

# Test message
oracle channels test telegram --message "Test"
```

---

## Resources

- **Documentation:** https://docs.oracle.ai
- **API Reference:** https://api.oracle.ai/docs
- **Community Discord:** https://discord.gg/oracle
- **Issue Tracker:** https://github.com/oracle-ai/oracle/issues

---

*Last Updated: 2026-03-15*
