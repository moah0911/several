# Repository Guidelines

## Project Structure & Module Organization
This repo now contains an MVP Python CLI/TUI implementation for `Several`.
- Specs in `docs/`: `docs/PRD.md`, `docs/technical_design.md`, `docs/command_specification.md`, `docs/security_model.md`, `docs/testing_strategy.md`, `docs/user_documentation.md`.
- Storage/runtime reference in `docs/`: `docs/filesystem_and_storagedesgin.md`, `docs/hardware_and_resources.md`, `docs/packaging_and_distribution.md`.
- Code layout: `src/several/{cli.py,tui/,core/,adapters/,config/}` and `tests/`.

Keep architecture, command contracts, security, and tests in separate docs; cross-link instead of duplicating.

## Build, Test, and Development Commands
Use these commands as implementation is scaffolded:
- `. .venv/bin/activate` activate local virtual environment.
- `python3 -m pip install -r requirements-dev.txt` install runtime + dev tools.
- `python3 -m compileall src` syntax check.
- `python3 -m ruff check src tests` lint check.
- `pytest -m unit --cov=several --cov-report=term-missing` run unit tests.
- `pytest -m integration -v` run integration tests.
- `pytest -m e2e -v --timeout=300` run end-to-end tests.
- `several run` launch TUI; `several task -a claude,codex "Refactor module"` for CLI mode.
- Always run through the local environment: `. .venv/bin/activate` then use `python3`/`pytest`.

## Coding Style & Naming Conventions
Python conventions from the test/package specs:
- Format with `black` (line length 100).
- Lint with `ruff`; type-check with strict `mypy`.
- Prefer typed, modular orchestration code in `core/` and adapter-specific code in `adapters/`.
- Test names: `test_<module>_<scenario>_<expected_result>`.

For docs, keep short technical sections with explicit assumptions and acceptance criteria.

## Testing Guidelines
Target pyramid and gates:
- 70% unit, 20% integration, 10% e2e.
- Minimum coverage gate: 80% (`--cov-fail-under=80`).
- Coverage gate currently targets core/adapters/storage modules; interactive entry surfaces are omitted in `pyproject.toml`.
- Use markers: `unit`, `integration`, `e2e`, `security`, `slow`, `flaky`.
- Include specialized suites: `tests/security/`, `tests/performance/`, `tests/concurrency/`.

## Commit & Pull Request Guidelines
Git history is not available in this workspace, so follow explicit conventions:
- Imperative commit subjects (example: `Implement agent process wrapper`).
- One logical change per commit, with tests/docs in the same PR when relevant.
- PRs include: summary, affected specs/modules, test evidence, and follow-ups.
- Include terminal screenshots only when TUI behavior/layout changes.

## Agent-Specific Notes
Before coding, reconcile with: `technical_design.md`, `command_specification.md`, `security_model.md`, and `testing_strategy.md`. If specs conflict, document the decision in the changed file and keep command behavior aligned with `user_documentation.md`.
For task execution changes, preserve workspace isolation behavior in `src/several/core/workspace.py` and keep cleanup policy aligned with `storage.workspace_cleanup`.
Keep CLI and TUI task execution paths consistent by routing both through shared orchestration logic in `src/several/cli.py`.
When adding execution telemetry, persist both final task results (`task_results`) and stream events (`task_events`) in `src/several/core/db.py`.
Treat reporter/event-persistence paths as best-effort only: failures there must not terminate agent execution.
Maintain runner timeout correctness for silent subprocesses (no output/newline) and keep regression tests in `tests/test_runner.py` green.
