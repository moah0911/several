       # User Documentation

## Several: Universal AI Agent Orchestrator

**Version:** 1.0.0  
**Date:** 2026-02-21  
**Status:** Draft  

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Core Concepts](#core-concepts)
5. [Using the TUI](#using-the-tui)
6. [CLI Reference](#cli-reference)
7. [Configuration](#configuration)
8. [Adding Custom Agents](#adding-custom-agents)
9. [Workflows](#workflows)
10. [Troubleshooting](#troubleshooting)

---

## 1. Introduction

**Several** is a terminal-based orchestrator for AI coding agents. It allows you to run multiple agents (Claude Code, OpenAI Codex, Google Gemini, Qwen Code, and more) simultaneously from a single interface, with real-time progress tracking and output comparison.

### Why Several?

- **Parallel Execution**: Run the same task across multiple AI models simultaneously
- **Unified Interface**: Control all agents from one TUI—no more terminal juggling
- **Visual Progress**: See tqdm-style progress bars for each running agent
- **Zero Configuration**: Auto-detects installed agents, works out of the box
- **Extensible**: Add any CLI-based AI tool via YAML configuration

---

## 2. Installation

### Requirements

- Python 3.9+
- Terminal with 256-color support
- At least one AI agent CLI installed (Claude Code, Codex, etc.)

### Install Several

```bash
# Via pip (recommended)
pip install several

# Via Homebrew (macOS)
brew tap several-ai/tap
brew install several-ai

# Via AUR (Arch Linux)
yay -S several-ai

# From source
git clone https://github.com/several-ai/several.git
cd several
pip install -e .
```

### Verify Installation

```bash
several --version
# Output: several 1.0.0

several doctor
# Checks dependencies and configuration
```

---

## 3. Quick Start

### 3.1 First Launch

```bash
# Start the TUI
several

# Or with specific agents
several -a claude,codex
```

You'll see the main dashboard:

```
┌─────────────────────────────────────────────────────────────────┐
│  Several v1.0.0                                    [q]uit [h]elp │
├─────────────────────────────────────────────────────────────────┤
│  Task: [Type here and press Enter...]                           │
├─────────────────┬─────────────────┬─────────────────┬───────────┤
│  🤖 CLAUDE      │  🤖 CODEX       │  🤖 GEMINI      │  + Add    │
│  ● Idle         │  ● Idle         │  ○ Not Found    │   Agent   │
│                 │                 │                 │           │
│                 │                 │                 │           │
├─────────────────┴─────────────────┴─────────────────┴───────────┤
│  [Enter new task] [Run All] [Stop All] [Compare] [Export]       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Your First Task

1. **Type a task** in the input box at the bottom
2. **Press Enter** to send to all active agents
3. **Watch progress** bars update in real-time
4. **View results** in each agent pane
5. **Press `Tab`** to switch between panes

---

## 4. Core Concepts

### 4.1 Agents

Agents are external CLI tools that Several orchestrates. Several **does not** include AI models—it connects to tools you already have installed.

| Agent | Install Command | Several Auto-Detects |
|-------|----------------|----------------------|
| Claude Code | `npm install -g @anthropic-ai/claude-code` | ✅ Yes |
| OpenAI Codex | `npm install -g @openai/codex` | ✅ Yes |
| Google Gemini | `gemini install` (see docs) | ✅ Yes |
| Qwen Code | `pip install qwen-code` | ✅ Yes |
| Custom | Your own tool | ✅ Via config |

### 4.2 Execution Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Parallel** (default) | All agents run simultaneously | Compare approaches, maximize speed |
| **Sequential** | Output of Agent A → Input of Agent B | Pipeline: generate → review → test |

### 4.3 Workspaces

Each agent runs in an isolated **git worktree** (copy of your project). This prevents:
- Agents interfering with each other
- Accidental modifications to your main working directory
- Cross-contamination of changes

Workspaces are automatically cleaned up after tasks complete.

---

## 5. Using the TUI

### 5.1 Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Header: Several version, session info, global shortcuts       │
├─────────────────────────────────────────────────────────────┤
│ Agent Grid: Split panes showing each agent's status          │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐                        │
│ │ CLAUDE  │ │  CODEX  │ │ GEMINI  │  ...more agents         │
│ │ [progress]│ │ [progress]│ │ [progress]│                        │
│ │ output...│ │ output...│ │ output...│                        │
│ └─────────┘ └─────────┘ └─────────┘                        │
├─────────────────────────────────────────────────────────────┤
│ Input Bar: Type tasks, see history, autocomplete             │
├─────────────────────────────────────────────────────────────┤
│ Status Bar: Active agents, total tokens, system status       │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Keyboard Shortcuts

#### Global

| Key | Action |
|-----|--------|
| `q` or `Ctrl+C` | Quit Several |
| `?` or `F1` | Show help |
| `Tab` | Cycle focus between panes |
| `Ctrl+L` | Refresh screen |
| `Ctrl+S` | Save session |
| `Ctrl+N` | New task |

#### Agent Panes

| Key | Action |
|-----|--------|
| `Enter` | Open agent detail view |
| `Space` | Pause/resume agent |
| `k` | Kill agent |
| `r` | Restart agent |
| `l` | View full logs |
| `e` | Export agent output |
| `c` | Copy output to clipboard |
| `1-9` | Focus agent pane 1-9 |

#### Input Panel

| Key | Action |
|-----|--------|
| `Enter` | Submit task to all selected agents |
| `Ctrl+Enter` | Submit to specific agent (prompts) |
| `↑` / `↓` | Navigate command history |
| `Ctrl+R` | Search history |
| `Ctrl+A` | Select all agents |
| `Ctrl+D` | Deselect all agents |

#### Layout

| Key | Action |
|-----|--------|
| `F2` | Cycle layout (grid/horizontal/vertical) |
| `F3` | Toggle sidebar |
| `F4` | Toggle log panel |
| `+` / `-` | Resize panels |
| `=` | Reset layout |

### 5.3 Mouse Support

Several supports mouse interactions:
- **Click** panes to focus
- **Click** buttons to activate
- **Scroll** in output panels
- **Drag** panel borders to resize

---

## 6. CLI Reference

### 6.1 Global Commands

```bash
several [options] <command>

Options:
  -c, --config DIR      Config directory (default: ~/.local/share/several/config)
  -d, --data-dir DIR    Data directory (default: ~/.local/share/several/data)
  -v, --verbose         Verbose output (repeat for debug)
  -q, --quiet           Suppress non-error output
  -V, --version         Show version
  -h, --help            Show help
```

### 6.2 Main Commands

#### `several run` (default)

Start the TUI dashboard.

```bash
several run [options]
several              # Shortcut

Options:
  -a, --agents LIST     Comma-separated agents to activate (default: auto-detect)
  -s, --session ID      Resume from session ID
  -l, --layout MODE     Layout: grid, horizontal, vertical (default: grid)
  --no-auto-detect      Disable auto-detection
```

#### `several task`

Execute a task without entering TUI (useful for scripts/CI).

```bash
several task [options] "<PROMPT>"

Options:
  -a, --agents LIST     Agents to use (default: all)
  -p, --parallel        Run in parallel (default)
  --sequential          Run sequentially
  -o, --output FORMAT   Output: json, markdown, raw (default: markdown)
  --save DIR            Save results to directory
  -t, --timeout SEC     Timeout per agent (default: 300)
  --compare             Enable diff/compare mode

Examples:
  several task -a claude,codex "Refactor auth module"
  several task --sequential -a codex,claude "Implement feature"
  several task -a claude -o json --save ./results "Fix bug"
```

#### `several agents`

Manage available agents.

```bash
several agents list [--installed] [--format table|json|yaml]
several agents add <NAME> --command <PATH> [options]
several agents remove <NAME>
several agents test <NAME> [--prompt "Test"]
```

#### `several sessions`

Manage sessions.

```bash
several sessions list [--active]
several sessions export <ID> [--output FILE] [--format FORMAT]
several sessions import <FILE>
several sessions delete <ID> [--force]
```

#### `several config`

Manage configuration.

```bash
several config get <KEY>
several config set <KEY> <VALUE>
several config edit              # Opens $EDITOR
several config reset [--force]
```

---

## 7. Configuration

### 7.1 Configuration File

Located at `~/.local/share/several/config/config.yaml`:

```yaml
# UI Settings
ui:
  theme: dark                    # dark, light, high-contrast
  layout: grid                   # grid, horizontal, vertical
  refresh_rate: 30               # UI updates per second
  animations: true               # Enable animations
  compact_mode: false            # Compact display

# Agent Settings
agents:
  auto_detect: true              # Auto-detect on startup
  detect_on_startup: true
  default_agents: []             # Default agents to activate
  extra_paths:                   # Additional PATH entries
    - /opt/ai-tools/bin
    - ~/.local/bin

# Performance
performance:
  max_concurrent_agents: 8       # Maximum parallel agents
  buffer_size: 65536             # Output buffer size
  default_timeout: 300           # Default agent timeout (seconds)

# Storage
storage:
  max_session_age_days: 30       # Auto-delete old sessions
  max_log_age_days: 7            # Log rotation
  compress_logs: true            # Compress old logs
  workspace_cleanup: on_exit     # immediate, on_exit, manual

# Keybindings (override defaults)
keybindings:
  quit: "ctrl+q"
  new_task: "ctrl+n"

# Logging
logging:
  level: info                    # debug, info, warning, error
  format: json                   # json, text
```

### 7.2 Environment Variables

| Variable | Description |
|----------|-------------|
| `SEVERAL_CONFIG_DIR` | Config directory override |
| `SEVERAL_DATA_DIR` | Data directory override |
| `SEVERAL_LOG_LEVEL` | Logging level override |
| `SEVERAL_NO_COLOR` | Disable colors |
| `SEVERAL_THEME` | UI theme override |

---

## 8. Adding Custom Agents

### 8.1 Simple Custom Agent

Create `~/.local/share/several/config/agents/my-agent.yaml`:

```yaml
name: my-custom-agent
command:
  binary: /usr/local/bin/my-ai
  args:
    - "--interactive"
    - "--workspace={workspace}"

detection:
  command: "my-ai --version"
  min_version: "1.0.0"

parsing:
  progress:
    regex: "Progress: (\\d+)%"
    group: 1
  tokens:
    regex: "Tokens: (\\d+)/(\\d+)"
    used_group: 1
    total_group: 2

ui:
  icon: "🚀"
  color: "#FF6B6B"
```

### 8.2 Advanced Configuration

```yaml
name: company-ai
description: "Internal company AI tool"

command:
  binary: /opt/company/bin/ai-cli
  args:
    - "--json-output"
    - "--workspace={workspace}"
    - "--prompt-file={prompt_file}"
  templates:
    workspace: "{workspace}"
    prompt_file: "{prompt_file}"

environment:
  inherit: true
  vars:
    COMPANY_API_KEY: "${COMPANY_API_KEY}"
  unset:
    - PYTHONPATH

detection:
  command: "ai-cli --version"
  parse_version: "version (\\d+\\.\\d+\\.\\d+)"
  min_version: "2.0.0"

capabilities:
  interactive: true
  file_editing: true
  command_execution: true
  streaming: true

parsing:
  progress:
    regex: "Progress: (\\d+)%"
  tokens:
    regex: "Tokens: (\\d+)/(\\d+)"
  tool_call:
    start_regex: "▶ Tool: (\\w+)"
    end_regex: "◀ Tool: (\\w+) done"

health:
  check_command: "ai-cli --ping"
  timeout: 5
```

### 8.3 Verify Custom Agent

```bash
several agents list          # Should show new agent
several agents test my-agent # Test connectivity
```

---

## 9. Workflows

### 9.1 Compare Multiple Models

Send the same task to Claude, Codex, and Gemini simultaneously:

```bash
several -a claude,codex,gemini
```

Then type: `"Review this function for security issues"`

View side-by-side outputs and compare approaches.

### 9.2 Pipeline: Generate → Review → Test

Chain agents sequentially:

```bash
several task --sequential -a codex,claude "Implement user authentication"
```

1. **Codex** generates implementation
2. **Claude** reviews the code for security issues

### 9.3 CI/CD Integration

```bash
# Automated code review in CI
several task \
  -a codex \
  -o json \
  --save ./ai-results \
  "Review PR for bugs and style issues"

# Check results
if [ -f ./ai-results/codex/findings.json ]; then
  echo "AI review completed"
fi
```

### 9.4 Session Management

```bash
# Start long-running session
several -s my-project

# Later, resume exactly where you left off
several -s my-project

# Export results
several sessions export my-project --output results.md
```

---

## 10. Troubleshooting

### 10.1 Common Issues

| Issue | Solution |
|-------|----------|
| Agent not detected | Check `which agent-name` works in shell |
| Permission denied | Ensure agent binary is executable |
| TUI not rendering | Check terminal supports 256 colors |
| Progress not showing | Some agents don't output progress; heuristics will estimate |
| Out of memory | Reduce `max_concurrent_agents` in config |
| Workspace errors | Ensure project is a git repository |

### 10.2 Debug Mode

```bash
# Verbose logging
several -vvv

# Check configuration
several config edit

# View logs
several logs --follow

# Test specific agent
several agents test claude --prompt "Hello"
```

### 10.3 Getting Help

- **Documentation**: `several --help` or `several <command> --help`
- **GitHub Issues**: https://github.com/several-ai/several/issues
- **Discord Community**: [link]
- **TUI Help**: Press `?` in the interface

### 10.4 Reset Everything

```bash
# Reset configuration
several config reset --force

# Clear all data
rm -rf ~/.local/share/several/data

# Fresh start
several
```

---

## Quick Reference Card

```
┌────────────────────────────────────────┐
│          SEVERAL CHEAT SHEET           │
├────────────────────────────────────────┤
│ START                                  │
│   several                              │
│   several -a claude,codex              │
│                                        │
│ IN TUI                                 │
│   Enter        Submit task             │
│   Tab          Switch panes            │
│   Space        Pause agent             │
│   k            Kill agent              │
│   r            Restart agent           │
│   1-9          Focus agent N           │
│   F2           Change layout           │
│   ?            Help                    │
│   q            Quit                    │
│                                        │
│ CLI MODE                               │
│   several task "prompt" -a claude      │
│   several agents list                  │
│   several sessions export <id>         │
│                                        │
│ CONFIG                                 │
│   ~/.local/share/several/config/       │
│   several config edit                  │
└────────────────────────────────────────┘
```

---
