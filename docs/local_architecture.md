 # Local Architecture Document

## Several: Universal AI Agent Orchestrator

**Version:** 1.0.0  
**Date:** 2026-02-21  


---

## 1. Architectural Overview

Several follows a **layered architecture** with clear separation between the TUI presentation layer, orchestration logic, and agent adapters. The system is designed to be modular, allowing new agents to be added without core code changes.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │  Dashboard  │  │ Agent Panes │  │  Task Input │  │  Logs   │ │
│  │   (Main)    │  │  (Split)    │  │   (Bottom)  │  │ (Side)  │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────┬────┘ │
│         └─────────────────┴─────────────────┴──────────────┘    │
│                              │                                   │
│                         Textual TUI Framework                    │
└──────────────────────────────┼───────────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────────┐
│                         ORCHESTRATION LAYER                      │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │                    Task Orchestrator                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │  │
│  │  │   Parser    │  │  Scheduler  │  │ State Manager   │    │  │
│  │  │  (Input)    │  │ (Parallel)  │  │   (SQLite)      │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘    │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │                  Agent Manager                             │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐  │  │
│  │  │ Discovery│ │ Lifecycle│ │  Health │ │   Registry      │  │  │
│  │  │ (Scan)  │ │(Start/Stop)│ │ (Check) │ │  (YAML/JSON)    │  │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────────┐
│                         ADAPTER LAYER                            │
│                              │                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   Claude    │  │    Codex    │  │   Gemini    │  │  Custom │ │
│  │   Adapter   │  │   Adapter   │  │   Adapter   │  │ Adapter │ │
│  │  (claude)   │  │   (codex)   │  │  (gemini)   │  │ (user)  │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────┬────┘ │
│         └─────────────────┴─────────────────┴──────────────┘    │
│                              │                                   │
│                    Process Wrapper (PTY)                         │
│                         │           │                            │
│                    ┌────┘           └────┐                       │
│                    ▼                      ▼                       │
│              [stdout/stderr]      [stdin injection]              │
│                    │                      │                       │
└────────────────────┼──────────────────────┼──────────────────────┘
                     │                      │
                     ▼                      ▼
            ┌─────────────┐          ┌─────────────┐
            │   Claude    │          │    Codex    │
            │    Code     │          │    CLI      │
            │  (external) │          │  (external) │
            └─────────────┘          └─────────────┘
```

---

## 2. Component Breakdown

### 2.1 Presentation Layer

**Technology:** Python `textual` (modern TUI framework)

| Component | Responsibility | Key Features |
|-----------|---------------|--------------|
| `Dashboard` | Main layout container | Grid layout, responsive panes |
| `AgentPane` | Per-agent display | Progress bar, status, mini-log |
| `TaskInput` | User command entry | History, auto-complete, validation |
| `LogPanel` | Aggregated output | Syntax highlighting, search |
| `StatusBar` | System status | Active agents, total tokens, errors |

**State Flow:**
```
User Input → TaskInput → Orchestrator → AgentPane updates ← Adapter events
                ↑___________________________________________|
```

### 2.2 Orchestration Layer

**Core Classes:**

```python
# Simplified architecture representation

class TaskOrchestrator:
    """Central coordinator for all agent operations"""
    - task_queue: asyncio.Queue
    - active_tasks: Dict[str, AgentTask]
    - event_bus: asyncio.Event
    
class AgentManager:
    """Manages agent lifecycle and discovery"""
    - registry: AgentRegistry
    - process_manager: ProcessManager
    - health_monitor: HealthMonitor
    
class StateManager:
    """SQLite-backed persistence"""
    - sessions: SessionStore
    - history: TaskHistory
    - metrics: MetricsStore
```

**Concurrency Model:**
- **asyncio** for I/O-bound operations (process communication)
- **ThreadPoolExecutor** for CPU-bound tasks (parsing, diffing)
- **One subprocess per agent** with PTY allocation for interactive support

### 2.3 Adapter Layer

**Pattern:** Strategy Pattern with Factory

```
BaseAdapter (abstract)
    ├── ClaudeAdapter
    ├── CodexAdapter  
    ├── GeminiAdapter
    ├── QwenAdapter
    └── CustomAdapter (YAML-defined)
```

**Adapter Responsibilities:**
1. **Command Construction**: Build CLI invocation string
2. **Process Spawning**: Start subprocess with proper env/args
3. **Stream Parsing**: Parse stdout/stderr for progress/events
4. **Event Emission**: Send structured events to Orchestrator
5. **Cleanup**: Graceful shutdown and resource cleanup

**Event Types:**
```python
class AgentEvent:
    STARTED
    PROGRESS_UPDATE  # % complete, tokens used
    OUTPUT_CHUNK     # stdout/stderr data
    TOOL_CALL        # file edit, command run
    COMPLETED
    ERROR
    USER_INPUT_REQUIRED  # y/n prompt detected
```

---

## 3. Data Flow

### 3.1 Task Execution Flow

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────┐
│  User   │────▶│  TaskInput  │────▶│ Orchestrator│────▶│  Parse  │
│         │     │             │     │             │     │  Task   │
└─────────┘     └─────────────┘     └──────┬──────┘     └────┬────┘
                                           │                  │
                                           ▼                  ▼
                                    ┌─────────────┐     ┌─────────┐
                                    │  Discovery  │◀────│  Route  │
                                    │   (Who's    │     │  to N   │
                                    │ available?) │     │ agents  │
                                    └──────┬──────┘     └─────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
              ┌─────────┐           ┌─────────┐           ┌─────────┐
              │ Adapter │           │ Adapter │           │ Adapter │
              │ Claude  │           │  Codex  │           │ Gemini  │
              └────┬────┘           └────┬────┘           └────┬────┘
                   │                      │                      │
                   ▼                      ▼                      ▼
              ┌─────────┐           ┌─────────┐           ┌─────────┐
              │ Process │           │ Process │           │ Process │
              │ Spawn   │           │ Spawn   │           │ Spawn   │
              └────┬────┘           └────┬────┘           └────┬────┘
                   │                      │                      │
                   └──────────────────────┼──────────────────────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │ Event Stream│
                                   │  (asyncio)  │
                                   └──────┬──────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
                    ▼                     ▼                     ▼
              ┌─────────┐          ┌─────────┐          ┌─────────┐
              │  Update │          │  Update │          │  Update │
              │  Claude │          │  Codex  │          │  Gemini │
              │  Pane   │          │  Pane   │          │  Pane   │
              │ (tqdm)  │          │ (tqdm)  │          │ (tqdm)  │
              └─────────┘          └─────────┘          └─────────┘
```

### 3.2 Progress Tracking

Since external CLIs don't expose progress APIs, Several uses **heuristics**:

| Signal | Progress Indicator |
|--------|-------------------|
| Token count increase | % of context window |
| Tool calls (file edits) | % of expected edits |
| Time elapsed | Timeout-based estimate |
| Output size | Relative to task complexity |
| Idle time | Stall detection |

**Progress Bar Update:**
```python
# Pseudo-code for progress calculation
def calculate_progress(agent_state) -> float:
    signals = [
        token_progress(agent_state.tokens_used),
        tool_call_progress(agent_state.tools_called),
        time_based_estimate(agent_state.start_time),
        output_size_heuristic(agent_state.output_buffer)
    ]
    return weighted_average(signals, weights=[0.4, 0.3, 0.2, 0.1])
```

---

## 4. Process Management

### 4.1 Subprocess Architecture

```
┌─────────────────────────────────────────┐
│           Several (Python)              │
│  ┌─────────────────────────────────┐    │
│  │      ProcessManager             │    │
│  │  ┌─────────┐    ┌─────────┐    │    │
│  │  │  PTY    │◀──▶│  stdin  │    │    │
│  │  │ Master  │    │ writer  │    │    │
│  │  └────┬────┘    └─────────┘    │    │
│  └───────┼─────────────────────────┘    │
└──────────┼──────────────────────────────┘
           │ fork/exec
           ▼
┌─────────────────────────────────────────┐
│           Child Process                 │
│  ┌─────────┐    ┌─────────┐    ┌────┐ │
│  │  PTY    │───▶│  Agent  │───▶│stdout│ │
│  │  Slave  │◀───│  CLI    │◀───│stdin │ │
│  └─────────┘    └─────────┘    └────┘ │
└─────────────────────────────────────────┘
```

**Key Design Decisions:**
- **PTY (Pseudo-Terminal)**: Required for CLIs that do isatty() checks (colors, interactive prompts)
- **Non-blocking I/O**: Using `asyncio` streams with `selector`
- **Buffer Management**: Circular buffers to prevent memory bloat on verbose agents

### 4.2 Signal Handling

| Signal | Action |
|--------|--------|
| SIGINT (Ctrl+C) | Graceful shutdown of all agents, save state |
| SIGTERM | Immediate cleanup, preserve logs |
| SIGHUP | Reload configuration, restart agents |
| Agent SIGCHLD | Cleanup zombie processes, update status |

---

## 5. Storage Architecture

### 5.1 SQLite Schema

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    sessions     │     │     tasks       │     │    outputs      │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │◀────┤ session_id (FK) │     │ task_id (FK)    │
│ created_at      │     │ agent_name      │────▶│ id (PK)         │
│ name            │     │ prompt          │     │ content         │
│ config_json     │     │ status          │     │ tokens_used     │
│ status          │     │ started_at      │     │ metadata_json   │
└─────────────────┘     │ completed_at    │     └─────────────────┘
                        │ exit_code       │
                        │ output_id (FK)  │◀────┘
                        └─────────────────┘
                               │
                        ┌─────────────────┐
                        │    metrics      │
                        ├─────────────────┤
                        │ task_id (FK)    │
                        │ latency_ms      │
                        │ tokens_in       │
                        │ tokens_out      │
                        │ cost_estimate   │
                        └─────────────────┘
```

### 5.2 File System Layout

```
~/.local/share/several/
├── config/
│   ├── config.yaml          # Main configuration
│   └── agents/              # Custom agent definitions
│       ├── custom-agent.yaml
│       └── legacy-tool.yaml
├── data/
│   ├── several.db           # SQLite database
│   ├── sessions/            # Session exports
│   └── cache/               # Temporary agent outputs
├── logs/
│   ├── several.log          # Application logs
│   └── agents/              # Per-agent debug logs
│       ├── claude-20250221-143022.log
│       └── codex-20250221-143022.log
└── state/
    └── resume.json          # Crash recovery state
```

---

## 6. Communication Patterns

### 6.1 Internal Event Bus

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Adapter   │────▶│  Event Bus  │◀────│   TUI       │
│  (Producer) │     │ (asyncio    │     │ (Consumer)  │
│             │     │  Queue)     │     │             │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │  Subscribers  │
                    │  - Logger     │
                    │  - Metrics    │
                    │  - StateMgr   │
                    └─────────────┘
```

**Event Schema (JSON):**
```json
{
  "event_id": "uuid",
  "timestamp": "2026-02-21T14:30:22Z",
  "agent_id": "claude-001",
  "type": "PROGRESS_UPDATE",
  "payload": {
    "percent": 45,
    "tokens_used": 2400,
    "current_tool": "read_file",
    "message": "Analyzing auth module..."
  }
}
```

### 6.2 Inter-Process Communication

Several uses **stdout/stderr parsing** rather than APIs:

```
Agent Output Stream
    │
    ├──▶ "[Progress: 45%]" ─────▶ Parsed ────▶ Progress Bar
    │
    ├──▶ "I'll help you..." ────▶ Parsed ────▶ Output Panel
    │
    ├──▶ "Running: npm test" ───▶ Parsed ────▶ Tool Call Log
    │
    └──▶ "Error: ..." ──────────▶ Parsed ────▶ Error Notification
```

**Parsing Strategy:**
- Regex patterns for known output formats
- Heuristic detection for unknown formats
- Configurable parsers per agent

---

## 7. Extensibility

### 7.1 Custom Agent Definition (YAML)

```yaml
# ~/.local/share/several/config/agents/my-custom-agent.yaml
name: my-custom-agent
command: my-ai-tool
args:
  - "--interactive"
  - "--cwd={workspace}"
env:
  MY_API_KEY: "${MY_API_KEY}"
detection:
  command: which my-ai-tool
  min_version: "1.0.0"
parsing:
  progress_regex: 'Progress: (\d+)%'
  token_regex: 'Tokens used: (\d+)'
  error_regex: 'ERROR: (.+)'
ui:
  icon: 🤖
  color: "#FF6B6B"
  label: "My Agent"
```

### 7.2 Plugin Hook System (Future)

```
Hook Points:
├── pre_task_start(agent, task)
├── post_task_complete(agent, task, result)
├── on_output_chunk(agent, chunk)
├── on_tool_call(agent, tool_call)
└── on_error(agent, error)
```

---

## 8. Security Considerations

| Layer | Measure |
|-------|---------|
| Process Isolation | Each agent in separate subprocess |
| Environment Sanitization | Clean env vars, no secrets in logs |
| File System | Sandboxed to workspace directory |
| Input Validation | Escape shell injection attempts |
| Audit Logging | All commands logged with timestamps |

---

## 9. Performance Targets

| Metric | Target | Strategy |
|--------|--------|----------|
| UI Latency | < 16ms (60fps) | Async rendering, debounced updates |
| Agent Spawn | < 500ms | Lazy import, connection pooling |
| Memory/Agent | < 50MB overhead | Streaming output, no buffering |
| Max Agents | 16 concurrent | Process limits, backpressure |
| Startup Time | < 2 seconds | Compiled bytecode, lazy loading |

---

## 10. Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| TUI Framework | `textual` | Rich widgets, CSS-like styling, asyncio-native |
| Process Mgmt | `asyncio` + `pty` | Cross-platform PTY support |
| Database | `sqlite3` + `aiosqlite` | Zero-config, portable, async |
| Config | `pydantic` + YAML | Validation, type safety |
| CLI Parsing | `typer` | Clean command definitions |
| Logging | `structlog` | Structured, performant |
| Testing | `pytest` + `pytest-asyncio` | Async test support |

---
