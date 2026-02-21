
---

# Product Requirements Document (PRD)

## Several: Universal AI Agent Orchestrator

**Version:** 1.0.0  
**Date:** 2026-02-21  


---

## 1. Executive Summary

Several is a **Terminal User Interface (TUI)** application that allows users to orchestrate multiple AI coding agents (Claude Code, Codex, Gemini CLI, Qwen Code, etc.) from a single unified interface. Unlike existing solutions that require web UIs or tmux splits, Several provides a native terminal experience with real-time progress tracking, parallel execution, and centralized task management.

### Core Value Proposition
- **One Interface, Many Agents**: Control Claude, Codex, Gemini, Qwen, and any CLI-based AI tool from one dashboard
- **Parallel Execution**: Run tasks across different agents simultaneously
- **Visual Progress**: Real-time tqdm-style progress bars for each agent
- **Zero Configuration**: Uses whatever tools are already installed on the user's system
- **Extensible**: Add new agents via simple configuration files

---

## 2. Problem Statement

### Current Pain Points
1. **Fragmented Workflow**: Developers must open multiple terminal windows/tmux panes to use different AI agents
2. **No Unified Visibility**: Cannot see status of all running agents at a glance
3. **Manual Coordination**: Running the same task across multiple agents requires manual copy-pasting
4. **No Progress Indication**: CLI agents don't show visual progress for long-running tasks
5. **Tool Sprawl**: Each agent has different invocation patterns and output formats

### Target Users
- **AI-First Developers**: Who use multiple LLMs for different tasks (Claude for architecture, Codex for implementation, etc.)
- **Vibe Coders**: Who want to compare outputs across models simultaneously
- **DevOps Engineers**: Managing infrastructure across multiple AI-assisted workflows
- **Technical Leads**: Reviewing AI-generated code from various sources

---

## 3. Product Vision

```
┌─────────────────────────────────────────────────────────────────┐
│  Several v1.0.0                                    [q]uit [h]elp │
├─────────────────────────────────────────────────────────────────┤
│  Task: "Refactor authentication module to use JWT"               │
├─────────────────┬─────────────────┬─────────────────┬───────────┤
│   CLAUDE        │   CODEX         │   GEMINI        │  + Add    │
│  ●●●●○○○○ 45%   │  ●●●●●●○○ 60%   │  ●●●○○○○○ 25%   │   Agent   │
│  Status: Coding │  Status: Testing│  Status: Analyz │           │
│  Tokens: 2.4k   │  Tokens: 1.8k   │  Tokens: 900    │           │
├─────────────────┴─────────────────┴─────────────────┴───────────┤
│  [Enter new task] [Run All] [Stop All] [Compare] [Export]       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Functional Requirements

### 4.1 Core Features

| ID | Feature | Priority | Description |
|----|---------|----------|-------------|
| F1 | Agent Discovery | P0 | Auto-detect installed CLI tools (claude, codex, gemini, qwen, etc.) |
| F2 | Task Distribution | P0 | Send same task to multiple agents in parallel |
| F3 | Progress Visualization | P0 | Real-time progress bars with token/usage stats |
| F4 | Individual Control | P0 | Start/stop/restart individual agents |
| F5 | Output Aggregation | P1 | Collect and display results in unified view |
| F6 | Diff/Compare Mode | P1 | Side-by-side comparison of agent outputs |
| F7 | Session Persistence | P1 | Save/load task history and configurations |
| F8 | Custom Agents | P2 | Add arbitrary CLI tools via YAML config |
| F9 | Export Results | P2 | Save outputs to files or clipboard |
| F10 | Keyboard Navigation | P0 | Full vim-style keybindings |

### 4.2 Agent Support Matrix

| Agent | Command | Detection | Status |
|-------|---------|-----------|--------|
| Claude Code | `claude` | `which claude` | Planned |
| OpenAI Codex | `codex` | `which codex` | Planned |
| Gemini CLI | `gemini` | `which gemini` | Planned |
| Qwen Code | `qwen-code` | `which qwen-code` | Planned |
| Mistral Vibe | `mistral-vibe` | `which mistral-vibe` | Planned |
| Aider | `aider` | `which aider` | Planned |
| Custom | User-defined | Config file | Planned |

---

## 5. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| N1 | Performance | Support 8+ simultaneous agents without UI lag |
| N2 | Memory | < 200MB RAM for orchestrator itself |
| N3 | Startup | < 2 seconds to interactive TUI |
| N4 | Compatibility | Linux, macOS, Windows (WSL) |
| N5 | Terminal | Support 256-color and true-color terminals |
| N6 | Responsiveness | UI updates at 30fps during agent execution |

---

## 6. User Stories

### Story 1: Parallel Architecture Review
> As a tech lead, I want to send a system design task to both Claude and Gemini simultaneously, so I can compare their architectural recommendations side-by-side.

**Acceptance Criteria:**
- Can input task once and distribute to N agents
- See real-time progress for each agent
- View outputs in split-pane or tabbed interface
- Export both responses to markdown files

### Story 2: Progressive Enhancement
> As a developer, I want to run a refactoring task on Codex first, then automatically send the result to Claude for review, creating a pipeline.

**Acceptance Criteria:**
- Chain agents sequentially (output of A → input of B)
- Visual pipeline builder in TUI
- Pause/resume between stages

### Story 3: Agent Farm
> As an AI researcher, I want to run the same prompt across 5 different models and see which performs best, with token usage comparison.

**Acceptance Criteria:**
- Execute identical prompts in parallel
- Token usage and cost tracking per agent
- Ranking/scoring interface
- Export comparison matrix

---

## 7. Technical Constraints

1. **No Model Provisioning**: Several ONLY orchestrates existing CLI tools. It does not download, install, or provide AI models.
2. **CLI Wrapping**: Must wrap existing CLIs without modifying them (stdout/stderr capture).
3. **No Root Required**: User-space installation only.
4. **Stateless Core**: Core orchestrator is stateless; state stored in SQLite locally.

---

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| Time to first task | < 30 seconds |
| Agent setup time | 0 (auto-detect) |
| Parallel agent support | 8+ |
| User retention (7-day) | 40% |
| GitHub stars (6 months) | 1000+ |

---

## 9. Out of Scope (v1.0)

- Web UI (terminal-only)
- Built-in AI models or API keys
- Cloud synchronization
- Multi-user collaboration
- Plugin marketplace (use config files instead)

---

## 10. Roadmap

| Phase | Timeline | Deliverables |
|-------|----------|--------------|
| Alpha | Week 1-2 | Core TUI, 3 agents, basic progress |
| Beta | Week 3-4 | 6 agents, compare mode, persistence |
| v1.0 | Week 5-6 | 8+ agents, pipelines, polish |
| v1.1 | Month 3 | Custom configs, export formats |

---

## 11. Open Questions

1. Should we support remote agents via SSH, or local-only?
2. How to handle agents that require interactive input (y/n prompts)?
3. Should we implement a plugin API or stick to YAML configs?
4. Integration with IDE extensions (VSCode, JetBrains)?

---
