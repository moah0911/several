  # Command Specification

## Several: Universal AI Agent Orchestrator

**Version:** 1.0.0  
**Date:** 2026-02-21  
**Status:** Draft  

---

## 1. Command Overview

Several provides a unified command interface accessible via the `several` (or `svr`) command. All operations are available both as CLI commands and within the TUI.

### Command Structure

```
several [GLOBAL_OPTIONS] <COMMAND> [COMMAND_OPTIONS] [ARGS]
```

---

## 2. Global Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--config` | `-c` | Path to config directory | `~/.local/share/several/config` |
| `--data-dir` | `-d` | Path to data directory | `~/.local/share/several/data` |
| `--verbose` | `-v` | Enable verbose logging (repeat for debug) | `false` |
| `--quiet` | `-q` | Suppress non-error output | `false` |
| `--version` | `-V` | Show version and exit | - |
| `--help` | `-h` | Show help message | - |

---

## 3. Core Commands

### 3.1 `several run` - Launch TUI Dashboard

**Description:** Start the interactive TUI dashboard (default command).

```bash
several run [OPTIONS]
several           # Alias for 'several run'
```

**Options:**

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--agents` | `-a` | Comma-separated list of agents to activate | `auto` |
| `--session` | `-s` | Resume from session ID | `new` |
| `--layout` | `-l` | Layout mode: `grid`, `horizontal`, `vertical` | `grid` |
| `--no-auto-detect` | - | Disable automatic agent discovery | `false` |

**Examples:**

```bash
several                          # Start with auto-detected agents
several -a claude,codex          # Start with specific agents only
several -s session-abc123        # Resume previous session
several -l horizontal            # Use horizontal split layout
```

---

### 3.2 `several task` - Execute Task (CLI Mode)

**Description:** Execute a task across specified agents without entering TUI. Useful for scripting.

```bash
several task [OPTIONS] "<PROMPT>"
```

**Options:**

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--agents` | `-a` | Agents to use (comma-separated) | `all` |
| `--parallel` | `-p` | Run in parallel | `true` |
| `--sequential` | - | Run sequentially (chain output) | `false` |
| `--output` | `-o` | Output format: `json`, `markdown`, `raw` | `markdown` |
| `--save` | - | Save results to directory | - |
| `--timeout` | `-t` | Timeout per agent (seconds) | `300` |
| `--compare` | - | Enable diff/compare mode | `false` |

**Examples:**

```bash
# Single task to all agents in parallel
several task -a claude,codex,gemini "Refactor auth module"

# Sequential pipeline: Codex → Claude review
several task --sequential -a codex,claude "Implement login feature"

# Save outputs for CI/CD
several task -a codex -o json --save ./results "Fix bug #123"
```

**Output Format (JSON):**

```json
{
  "task_id": "uuid",
  "timestamp": "2026-02-21T14:30:00Z",
  "prompt": "Refactor auth module",
  "results": [
    {
      "agent": "claude",
      "status": "completed",
      "exit_code": 0,
      "output": "...",
      "tokens_used": 2400,
      "duration_ms": 45000,
      "files_modified": ["src/auth.js"]
    },
    {
      "agent": "codex",
      "status": "completed", 
      "exit_code": 0,
      "output": "...",
      "tokens_used": 1800,
      "duration_ms": 32000,
      "files_modified": ["src/auth.js", "tests/auth.test.js"]
    }
  ]
}
```

---

### 3.3 `several agents` - Agent Management

**Description:** Manage available AI agents.

#### `several agents list`

```bash
several agents list [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--installed` | Show only installed/detected agents |
| `--available` | Show all supported agents |
| `--format` | Output format: `table`, `json`, `yaml` |

**Example Output:**

```
┌─────────┬──────────┬─────────┬──────────┬─────────────────┐
│ Agent   │ Status   │ Version │ Type     │ Path            │
├─────────┼──────────┼─────────┼──────────┼─────────────────┤
│ claude  │ ● active │ 0.2.45  │ official │ /usr/bin/claude │
│ codex   │ ● active │ 1.0.0   │ official │ /usr/bin/codex  │
│ gemini  │ ○ absent │ -       │ official │ Not found       │
│ qwen    │ ● active │ 0.1.2   │ custom   │ ~/bin/qwen-code │
└─────────┴──────────┴─────────┴──────────┴─────────────────┘
```

#### `several agents add`

```bash
several agents add <NAME> --command <PATH> [OPTIONS]
```

**Options:**

| Option | Description | Required |
|--------|-------------|----------|
| `--command` | Path to executable | Yes |
| `--args` | Default arguments | No |
| `--env` | Environment variables (KEY=VAL,...) | No |
| `--detect-version` | Command to check version | No |
| `--parser` | Output parser profile | No |

**Example:**

```bash
several agents add my-agent \
  --command /usr/local/bin/my-ai \
  --args "--interactive,--json" \
  --env "API_KEY=$MY_API_KEY" \
  --parser generic
```

#### `several agents remove`

```bash
several agents remove <NAME>
```

#### `several agents test`

```bash
several agents test <NAME> [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--prompt` | Test prompt to send | Default: "Hello" |
| `--timeout` | Test timeout | Default: 30s |

---

### 3.4 `several sessions` - Session Management

**Description:** Manage persistent sessions.

#### `several sessions list`

```bash
several sessions list [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--active` | Show only active sessions |
| `--format` | Output format |

**Example Output:**

```
┌─────────────────┬─────────────────────┬──────────┬─────────┬──────────┐
│ Session ID      │ Created             │ Agents   │ Tasks   │ Status   │
├─────────────────┼─────────────────────┼──────────┼─────────┼──────────┤
│ sess-abc123     │ 2026-02-21 14:30:22 │ 3        │ 12      │ active   │
│ sess-def456     │ 2026-02-21 10:15:00 │ 2        │ 5       │ closed   │
└─────────────────┴─────────────────────┴──────────┴─────────┴──────────┘
```

#### `several sessions export`

```bash
several sessions export <SESSION_ID> [OPTIONS]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--output` | `-o` | Output file path |
| `--format` | `-f` | `markdown`, `json`, `html` |

#### `several sessions import`

```bash
several sessions import <FILE>
```

#### `several sessions delete`

```bash
several sessions delete <SESSION_ID> [--force]
```

---

### 3.5 `several config` - Configuration

**Description:** Manage Several configuration.

#### `several config get`

```bash
several config get <KEY>
```

#### `several config set`

```bash
several config set <KEY> <VALUE>
```

#### `several config edit`

```bash
several config edit  # Opens $EDITOR
```

#### `several config reset`

```bash
several config reset [--force]
```

**Configuration Keys:**

| Key | Description | Default |
|-----|-------------|---------|
| `ui.theme` | Color theme | `dark` |
| `ui.layout` | Default layout | `grid` |
| `ui.refresh_rate` | UI update frequency (Hz) | `30` |
| `agents.auto_detect` | Auto-detect on startup | `true` |
| `agents.timeout` | Default agent timeout (s) | `300` |
| `logging.level` | Log level | `info` |
| `logging.max_size` | Max log file size (MB) | `100` |

---

### 3.6 `several logs` - Log Management

```bash
several logs [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--follow` | Follow log output (tail -f) |
| `--agent` | Filter by agent name |
| `--since` | Show logs since time |
| `--level` | Filter by level (debug, info, error) |

---

## 4. TUI Keybindings

### Global Shortcuts

| Key | Action |
|-----|--------|
| `q` / `Ctrl+C` | Quit (graceful shutdown) |
| `?` / `F1` | Show help overlay |
| `Tab` | Cycle focus between panes |
| `Ctrl+L` | Refresh screen |
| `Ctrl+S` | Save current session |
| `Ctrl+E` | Export results |
| `Ctrl+N` | New task |
| `Ctrl+P` | Pause/resume all agents |
| `Ctrl+K` | Kill all agents |
| `1-9` | Focus agent pane N |
| `0` | Focus input panel |

### Agent Pane Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Open agent detail view |
| `Space` | Pause/resume this agent |
| `k` | Kill this agent |
| `r` | Restart this agent |
| `l` | View full logs |
| `o` | View output only |
| `e` | Export this agent's output |
| `c` | Copy output to clipboard |

### Input Panel Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Submit task |
| `Ctrl+Enter` | Submit to specific agent (prompts) |
| `↑` / `↓` | Navigate command history |
| `Ctrl+R` | Search history |
| `Tab` | Auto-complete agent names |
| `Ctrl+A` | Select all agents |
| `Ctrl+D` | Deselect all agents |

### Layout Shortcuts

| Key | Action |
|-----|--------|
| `F2` | Cycle layout (grid/horizontal/vertical) |
| `F3` | Toggle sidebar |
| `F4` | Toggle log panel |
| `+` / `-` | Increase/decrease panel size |
| `=` | Reset layout |
| `g` | Toggle grid view (2x2, 3x3, etc.) |

---

## 5. Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SEVERAL_CONFIG_DIR` | Config directory | `~/.local/share/several/config` |
| `SEVERAL_DATA_DIR` | Data directory | `~/.local/share/several/data` |
| `SEVERAL_LOG_LEVEL` | Logging level | `info` |
| `SEVERAL_NO_COLOR` | Disable colors | `false` |
| `SEVERAL_THEME` | UI theme | `dark` |
| `EDITOR` | Default editor for config edit | `vi` |

---

## 6. Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Invalid usage/arguments |
| `3` | Configuration error |
| `4` | Agent not found |
| `5` | Agent execution failed |
| `6` | Timeout |
| `130` | Interrupted (Ctrl+C) |

---

## 7. Examples

### Daily Workflow Examples

```bash
# Morning standup - check what agents are available
several agents list

# Start working on a feature - use Claude for architecture, Codex for implementation
several -a claude,codex

# Inside TUI: Type task, hit Enter, both agents work in parallel

# Review mode - compare outputs from 3 agents
several task -a claude,codex,gemini --compare "Review this PR for security issues"

# CI/CD integration - run Codex for automated fixes
several task -a codex -o json --save ./results "Fix linting errors"

# Resume yesterday's session
several -s sess-abc123

# Custom agent for company internal tool
several agents add company-ai --command /opt/company-ai/cli --parser generic
several -a claude,codex,company-ai
```

---

## 8. Shell Integration

### Bash/Zsh Completion

```bash
# Generate completion script
several --generate-completion bash > /etc/bash_completion.d/several
several --generate-completion zsh > /usr/share/zsh/site-functions/_several
```

### Alias Suggestions

```bash
alias sv='several'
alias svr='several run'
alias svt='several task'
alias sva='several agents list'
alias svs='several sessions list'
```

---
