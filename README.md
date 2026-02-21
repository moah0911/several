# Several

Several is a terminal-first orchestrator for AI coding agents (Claude Code, Codex, Gemini CLI, Qwen, and compatible tools). It provides one TUI/CLI surface to run tasks in parallel, compare outputs, and manage sessions.

## Stack
- Python 3.9+ (recommended 3.11+)
- Textual + Rich for TUI
- Typer/Click for CLI
- SQLite (WAL mode) for state/session persistence
- YAML-based config and agent definitions

## Repository Structure

```text
src/several/
  cli.py
  tui/
  core/
  adapters/
  config/
tests/
docs/
pyproject.toml
```

## Implemented Command Surface (MVP)
- `several run` (default): launch dashboard
- `several task "<PROMPT>"`: non-interactive CLI mode
- `several agents ...`: list/add/remove/test adapters
- `several sessions ...`: list/export/import/delete sessions
- `several sessions tail <SESSION_ID>`: replay/poll persisted task events (including streamed output lines)
- `several config ...`: get/set/edit/reset config
- `several logs ...`: inspect log file output

Examples:

```bash
several run -a claude,codex
several task --sequential -a codex,claude "Implement auth and review"
several agents list --installed
```

## Current Documentation
- `docs/PRD.md`: requirements, scope, roadmap.
- `docs/technical_design.md`: architecture, components, concurrency model.
- `docs/command_specification.md`: complete CLI/TUI command contracts.
- `docs/filesystem_and_storagedesgin.md`: XDG layout, DB schema, worktree lifecycle.
- `docs/security_model.md`: threat model, validation, isolation, incident response.
- `docs/testing_strategy.md`: pyramid, pytest layout, CI matrix, quality gates.
- `docs/user_documentation.md`: installation, quick start, workflows, troubleshooting.
- `docs/packaging_and_distribution.md`: PyPI-first packaging and release channels.
- `docs/hardware_and_resources.md`: system/resource baselines and tuning.
- `docs/local_architecture.md`: local architecture details and data flow.

## Current Implementation Notes
- CLI, config, session persistence, and task execution are implemented in `src/several/`.
- TUI run mode supports interactive prompt submission from the input bar and executes tasks via the same orchestration path as CLI mode.
- Agent execution supports parallel and sequential modes using subprocess-based adapters.
- Session resume is implemented for `several run -s <session_id>` (restores session agents/layout by default).
- Adapter output parsing now extracts basic metrics (`tokens_used`, `% progress`, and tool-call hints) per run result.
- Session/task metadata is persisted in `several.db` under the configured data directory.
- Streamed task events are persisted in `task_events` and can be inspected via `sessions tail`.
- Runner timeout handling is robust even when agents produce no newline-delimited output.
- Reporter/persistence failures are isolated so task execution does not fail due to UI/log DB event handling.

## Reliability Checks Performed
- Full automated suite run in local `.venv` (`python3 -m pytest -q`), currently passing.
- Coverage gate is enforced at 80% (`--cov-fail-under=80`) and currently passes.
- Coverage scope omits interactive entry surfaces (`src/several/cli.py`, `src/several/tui/*`, `src/several/__main__.py`) so the gate targets core logic.
- Added regression tests for:
  - timeout behavior with no process output,
  - streaming output callbacks,
  - reporter exception isolation during task execution.
- Task runs now support per-agent git worktree isolation under `data/workspaces/<session>/<task>/<agent>` when executed inside a Git repository.
- Workspace cleanup follows `storage.workspace_cleanup` (currently `on_exit`/`immediate` clean at command end, `manual` preserves worktrees).

## Local Development
```bash
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 -m compileall src
python3 -m pytest -q
```
