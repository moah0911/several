    # File System & Storage Design

## Several: Universal AI Agent Orchestrator

**Version:** 1.0.0  
**Date:** 2026-02-21  
**Status:** Draft  

---

## 1. Overview

This document defines the file system structure, storage mechanisms, and data persistence strategy for Several. The design prioritizes portability, atomicity, and efficient retrieval while maintaining human-readable formats where practical.

---

## 2. Directory Structure

### 2.1 Base Directory Layout

```
~/.local/share/several/                    # XDG_DATA_HOME/several
├── config/                                # Configuration files
│   ├── config.yaml                        # Main configuration
│   ├── keybindings.yaml                   # Custom key mappings
│   ├── themes/                            # Custom themes
│   │   ├── dark-high-contrast.yaml
│   │   └── light.yaml
│   └── agents/                            # Custom agent definitions
│       ├── company-ai.yaml
│       └── legacy-tool.yaml
│
├── data/                                  # Runtime data
│   ├── several.db                         # SQLite database (WAL mode)
│   ├── several.db-shm                     # SQLite shared memory
│   ├── several.db-wal                     # SQLite write-ahead log
│   │
│   ├── sessions/                          # Session exports
│   │   ├── 2026-02-21/
│   │   │   ├── sess-abc123-export.md
│   │   │   └── sess-abc123-export.json
│   │   └── archive/
│   │       └── 2026-01-sessions.tar.gz
│   │
│   ├── cache/                             # Temporary caches
│   │   ├── completions/                   # Shell completion cache
│   │   ├── agent-metadata/                # Discovered agent info
│   │   └── http/                          # HTTP cache (if needed)
│   │
│   └── workspaces/                        # Agent working directories
│       └── temp/                          # Ephemeral workspaces
│           ├── claude-abc123-uuid/
│           ├── codex-abc123-uuid/
│           └── gemini-abc123-uuid/
│
├── logs/                                  # Application logs
│   ├── several.log                        # Current log
│   ├── several.log.1                      # Rotated log
│   ├── several.log.2.gz                   # Compressed old log
│   └── agents/                            # Per-agent debug logs
│       ├── claude-20250221-143022.log
│       ├── codex-20250221-143022.log
│       └── gemini-20250221-143022.log
│
└── state/                                 # Ephemeral state
    ├── pid                                # Running instance PID
    ├── socket                             # IPC socket (future)
    └── resume.json                        # Crash recovery state
```

### 2.2 XDG Compliance

| XDG Variable | Default | Several Path | Purpose |
|--------------|---------|--------------|---------|
| `XDG_DATA_HOME` | `~/.local/share` | `.../several/` | Persistent data |
| `XDG_CONFIG_HOME` | `~/.config` | `.../several/` | User configuration |
| `XDG_CACHE_HOME` | `~/.cache` | `.../several/` | Non-essential cache |
| `XDG_STATE_HOME` | `~/.local/state` | `.../several/` | State between restarts |

**Note:** Several consolidates all data under `XDG_DATA_HOME/several/` for simplicity, with subdirectories for config/cache/state.

---

## 3. SQLite Database Schema

### 3.1 Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    sessions     │       │     tasks       │       │  agent_results  │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │◀──────┤ session_id (FK) │       │ task_id (FK)    │
│ name            │       │ id (PK)         │◀──────┤ id (PK)         │
│ created_at      │       │ prompt          │       │ agent_id (FK)   │
│ updated_at      │       │ mode            │       │ status          │
│ config_json     │       │ timeout         │       │ output_text     │
│ status          │       │ created_at      │       │ exit_code       │
└─────────────────┘       │ started_at      │       │ tokens_used     │
                          │ completed_at    │       │ tokens_input    │
                          │ status          │       │ tokens_output   │
                          │ session_id      │       │ duration_ms     │
                          └─────────────────┘       │ files_modified  │
                                                    │ tool_calls_json │
                                                    │ error_message   │
                                                    │ created_at      │
                                                    └─────────────────┘
                                                           │
                              ┌────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │     agents      │
                    ├─────────────────┤
                    │ id (PK)         │
                    │ name            │
                    │ type            │
                    │ version         │
                    │ command_path    │
                    │ config_json     │
                    │ is_active       │
                    │ last_seen       │
                    │ created_at      │
                    └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│   task_events   │       │    metrics      │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ task_id (FK)    │       │ result_id (FK)  │
│ agent_id (FK)   │       │ latency_ms      │
│ event_type      │       │ tokens_per_sec  │
│ event_data_json │       │ memory_peak_mb  │
│ created_at      │       │ cpu_percent_avg │
└─────────────────┘       │ io_read_bytes   │
                          │ io_write_bytes  │
                          │ created_at      │
                          └─────────────────┘
```

### 3.2 Table Definitions

```sql
-- Sessions: Top-level container for related tasks
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,                    -- UUID v4
    name TEXT NOT NULL,                     -- User-defined or auto-generated
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    config_json TEXT NOT NULL DEFAULT '{}', -- Serialized config
    status TEXT DEFAULT 'active'            -- active, paused, closed, archived
);

-- Tasks: Individual user requests
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,                    -- UUID v4
    session_id TEXT NOT NULL,
    prompt TEXT NOT NULL,                   -- The actual user input
    mode TEXT DEFAULT 'parallel',           -- parallel, sequential
    timeout INTEGER DEFAULT 300,            -- Seconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'pending',          -- pending, running, completed, failed, cancelled
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Agents: Discovered and configured agents
CREATE TABLE agents (
    id TEXT PRIMARY KEY,                    -- e.g., 'claude', 'codex', 'custom-1'
    name TEXT NOT NULL UNIQUE,              -- Display name
    type TEXT NOT NULL,                     -- claude, codex, gemini, qwen, custom
    version TEXT,                           -- Detected version
    command_path TEXT NOT NULL,
    config_json TEXT NOT NULL DEFAULT '{}', -- Full agent config
    is_active BOOLEAN DEFAULT 1,
    last_seen TIMESTAMP,                    -- Last successful detection
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Results: Outcome of each agent execution
CREATE TABLE agent_results (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,                   -- completed, error, timeout, cancelled
    output_text TEXT,                       -- Full stdout/stderr capture
    output_truncated BOOLEAN DEFAULT 0,     -- Flag if output exceeded limit
    exit_code INTEGER,
    tokens_used INTEGER DEFAULT 0,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    duration_ms INTEGER,
    files_modified_json TEXT DEFAULT '[]',  -- Array of modified file paths
    tool_calls_json TEXT DEFAULT '[]',      -- Array of tool call objects
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

-- Task Events: Granular event log for replay/debugging
CREATE TABLE task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    agent_id TEXT,
    event_type TEXT NOT NULL,               -- start, progress, output, tool_call, complete, error
    event_data_json TEXT,                   -- Event-specific data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Metrics: Performance data for analysis
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id TEXT NOT NULL,
    latency_ms INTEGER,
    tokens_per_sec REAL,
    memory_peak_mb INTEGER,
    cpu_percent_avg REAL,
    io_read_bytes INTEGER,
    io_write_bytes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (result_id) REFERENCES agent_results(id) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX idx_tasks_session ON tasks(session_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_results_task ON agent_results(task_id);
CREATE INDEX idx_results_agent ON agent_results(agent_id);
CREATE INDEX idx_events_task ON task_events(task_id);
CREATE INDEX idx_events_created ON task_events(created_at);
```

### 3.3 Database Configuration

```sql
-- Performance optimizations
PRAGMA journal_mode = WAL;          -- Write-Ahead Logging for concurrency
PRAGMA synchronous = NORMAL;        -- Balance safety and speed
PRAGMA cache_size = 10000;          -- ~40MB cache
PRAGMA temp_store = MEMORY;         -- Temp tables in memory
PRAGMA mmap_size = 30000000000;     -- Memory-map large DBs
PRAGMA foreign_keys = ON;           -- Enforce referential integrity
```

---

## 4. Workspace Management

### 4.1 Git Worktree Strategy

Several uses **git worktrees** to provide isolated, reproducible environments for each agent-task combination.

```
Project Repository (.git)
    │
    ├── main worktree (user's working directory)
    │
    └── .git/worktrees/
        │
        ├── several-claude-abc123/     # Worktree for Claude
        │   ├── .several-agent         # Marker file
        │   ├── src/                   # Copy of source
        │   └── (agent writes here)
        │
        ├── several-codex-abc123/      # Worktree for Codex
        │   ├── .several-agent
        │   └── src/
        │
        └── several-gemini-abc123/     # Worktree for Gemini
            ├── .several-agent
            └── src/
```

### 4.2 Workspace Lifecycle

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────┐
│  Task   │────▶│   Create    │────▶│   Agent     │────▶│  Task   │
│ Created │     │  Worktree   │     │   Runs      │     │ Complete│
└─────────┘     └──────┬──────┘     └──────┬──────┘     └────┬────┘
                       │                    │                  │
                       ▼                    ▼                  ▼
              ┌──────────────┐      ┌──────────────┐  ┌──────────────┐
              │ git worktree │      │ Agent writes │  │  Diff vs     │
              │ add <path>   │      │ to worktree  │  │  main worktree│
              │ (sparse if   │      │              │  │              │
              │  possible)   │      │              │  │  User decides:│
              └──────────────┘      └──────────────┘  │  - Apply      │
                                                      │  - Discard    │
                                                      │  - Compare    │
                                                      └──────────────┘
```

### 4.3 Workspace Cleanup Policy

| Trigger | Action | Timing |
|---------|--------|--------|
| Task completion | Mark for deletion | Immediate |
| Session close | Delete worktrees | On close |
| Application exit | Delete orphaned | On startup scan |
| Scheduled job | Delete >7 days old | Weekly |

---

## 5. Log File Management

### 5.1 Log Rotation Strategy

```
several.log (current, max 100MB)
    │
    ├── several.log.1 (previous, max 100MB)
    │
    ├── several.log.2.gz (compressed)
    │
    ├── several.log.3.gz (compressed)
    │
    └── several.log.5.gz (oldest, then deleted)
```

### 5.2 Log Format

```json
{
  "timestamp": "2026-02-21T14:30:22.123456Z",
  "level": "INFO",
  "logger": "several.orchestrator",
  "message": "Task submitted",
  "context": {
    "task_id": "abc123",
    "agents": ["claude", "codex"],
    "prompt_preview": "Refactor auth module..."
  },
  "trace_id": "uuid-for-distributed-tracing"
}
```

### 5.3 Per-Agent Debug Logs

Separate logs for each agent instance to aid debugging without cluttering main log:

```
logs/agents/
├── claude-20250221-143022-abc123.log    # Full PTY capture
├── codex-20250221-143022-abc123.log
└── gemini-20250221-143022-abc123.log
```

**Contents:** Raw stdout/stderr with timestamps and escape sequences preserved.

---

## 6. Configuration File Formats

### 6.1 Main Configuration (YAML)

```yaml
# ~/.local/share/several/config/config.yaml
version: "1.0"

ui:
  theme: dark
  layout: grid
  refresh_rate: 30
  animations: true
  compact_mode: false
  
  # Panel sizing
  panel_ratio: [2, 1]  # Main:Sidebar
  min_panel_width: 40
  
  # Progress bars
  progress_style: tqdm  # tqdm, simple, none
  show_token_count: true
  show_time_estimate: true

agents:
  auto_detect: true
  detect_on_startup: true
  default_agents: []
  
  # Discovery paths (in addition to PATH)
  extra_paths:
    - /opt/ai-tools/bin
    - ~/.local/bin
  
  # Health check
  health_check_interval: 300  # seconds

performance:
  max_concurrent_agents: 8
  buffer_size: 65536
  parse_threads: 4
  max_output_buffer: 10MB
  
  # Timeouts
  default_timeout: 300
  cleanup_interval: 3600

storage:
  max_session_age_days: 30
  max_log_age_days: 7
  compress_logs: true
  
  # Database
  vacuum_interval: 86400  # Daily VACUUM
  
  # Workspaces
  workspace_cleanup: on_exit  # immediate, on_exit, manual

keybindings:
  # Override defaults
  quit: "ctrl+q"
  new_task: "ctrl+n"
  
logging:
  level: info
  format: json  # json, text
  destinations:
    - file
    - stderr  # Only if TTY

telemetry:
  enabled: false
  anonymized: true
```

### 6.2 Agent Definition (YAML)

```yaml
# ~/.local/share/several/config/agents/my-agent.yaml
version: "1.0"

meta:
  name: my-custom-agent
  description: "My company's internal AI tool"
  author: "Gowtham Boyina"
  icon: "🏢"
  color: "#4A90E2"

command:
  binary: /opt/company-ai/bin/ai-cli
  args:
    - "--interactive"
    - "--json-output"
    - "--workspace={workspace}"
    - "--session-id={session_id}"
  
  # Argument templates
  templates:
    workspace: "{workspace}"
    prompt_file: "{prompt_file}"  # Write prompt to temp file
    context_file: "{context_file}"  # JSON context

environment:
  inherit: true  # Inherit parent environment
  
  vars:
    COMPANY_AI_KEY: "${COMPANY_AI_KEY}"  # From shell env
    LOG_LEVEL: "debug"
  
  unset:
    - PYTHONPATH  # Remove problematic vars

detection:
  command: "ai-cli --version"
  parse_version: "version (\\d+\\.\\d+\\.\\d+)"
  min_version: "2.0.0"
  recommended_version: "2.5.0"

capabilities:
  interactive: true      # Supports interactive prompts
  file_editing: true     # Can modify files
  command_execution: true # Can run shell commands
  streaming: true        # Supports streaming output

parsing:
  # Progress indicators
  progress:
    regex: "Progress: (\\d+)%"
    group: 1
  
  # Token usage
  tokens:
    regex: "Tokens: (\\d+)/(\\d+)"
    used_group: 1
    total_group: 2
  
  # Tool calls
  tool_call:
    start_pattern: "▶ Tool: (\\w+)"
    end_pattern: "◀ Tool: (\\w+) done"
    args_pattern: "Args: (.*)"
  
  # Completion
  complete:
    pattern: "✓ Complete|✗ Failed"
    success_group: 0
  
  # Errors
  error:
    pattern: "Error: (.*)"
    fatal_pattern: "FATAL: (.*)"

health:
  check_command: "ai-cli --ping"
  timeout: 5
  interval: 60
```

---

## 7. Session Export Format

### 7.1 Markdown Export

```markdown
# Several Session Export

**Session ID:** sess-abc123  
**Created:** 2026-02-21 14:30:22  
**Exported:** 2026-02-21 15:45:00  

---

## Task 1: Refactor authentication module

**Submitted:** 14:30:25  
**Status:** ✅ Completed  
**Agents:** Claude, Codex, Gemini  

### Claude (claude-code v0.2.45)

**Status:** ✅ Completed  
**Duration:** 45.2s  
**Tokens:** 2,400 (in: 800, out: 1,600)  

**Output:**
```javascript
// src/auth.js - Refactored implementation
import jwt from 'jsonwebtoken';

export class AuthManager {
  // ... implementation ...
}
```

**Files Modified:**
- `src/auth.js` (rewritten)
- `src/auth.test.js` (added)

**Tool Calls:**
1. `read_file` - src/auth.js
2. `write_file` - src/auth.js
3. `run_command` - npm test

---

### Codex (codex v1.0.0)

**Status:** ✅ Completed  
**Duration:** 32.1s  
**Tokens:** 1,800  

**Output:**
```javascript
// Alternative implementation
const crypto = require('crypto');
// ...
```

---

### Comparison

| Aspect | Claude | Codex | Gemini |
|--------|--------|-------|--------|
| Lines Changed | 45 | 38 | 52 |
| Test Coverage | 100% | 85% | 90% |
| Security | JWT | Crypto | JWT |
| Duration | 45s | 32s | 28s |

---

## Task 2: Update documentation

...
```

### 7.2 JSON Export (Machine-Readable)

```json
{
  "export_version": "1.0",
  "session": {
    "id": "sess-abc123",
    "name": "Auth Refactoring",
    "created_at": "2026-02-21T14:30:22Z",
    "exported_at": "2026-02-21T15:45:00Z"
  },
  "tasks": [
    {
      "id": "task-xyz789",
      "prompt": "Refactor authentication module to use JWT",
      "mode": "parallel",
      "created_at": "2026-02-21T14:30:25Z",
      "completed_at": "2026-02-21T14:31:15Z",
      "results": [
        {
          "agent": {
            "id": "claude",
            "name": "Claude Code",
            "version": "0.2.45"
          },
          "status": "completed",
          "output": "...",
          "metrics": {
            "duration_ms": 45200,
            "tokens_input": 800,
            "tokens_output": 1600,
            "tokens_total": 2400
          },
          "files_modified": [
            {"path": "src/auth.js", "operation": "modified", "diff": "..."},
            {"path": "src/auth.test.js", "operation": "created", "content": "..."}
          ],
          "tool_calls": [
            {"tool": "read_file", "args": {"path": "src/auth.js"}, "timestamp": "..."},
            {"tool": "write_file", "args": {"path": "src/auth.js"}, "timestamp": "..."}
          ]
        }
      ]
    }
  ],
  "statistics": {
    "total_tasks": 5,
    "total_agents_used": 3,
    "total_tokens": 15000,
    "total_duration_ms": 245000
  }
}
```

---

## 8. Backup & Migration

### 8.1 Automatic Backups

| Trigger | Action | Retention |
|---------|--------|-----------|
| Daily | SQLite backup | 7 days |
| Pre-update | Full data backup | Until next update |
| Session close | Session export | 30 days |

### 8.2 Migration Strategy

```
Version Upgrade Path:
1.0.0 → 1.1.0 → 2.0.0

Migration Script:
1. Detect current schema version
2. Apply migrations sequentially
3. Validate data integrity
4. Create rollback point
5. Update schema version
```

---

## 9. Security Considerations

| Concern | Mitigation |
|---------|------------|
| **Sensitive data in logs** | Scrub API keys, tokens from output |
| **Workspace isolation** | Git worktrees prevent cross-contamination |
| **Database encryption** | Optional SQLCipher for at-rest encryption |
| **File permissions** | 0600 for config, 0700 for data dir |
| **Prompt history** | User-configurable retention, easy purge |

---
