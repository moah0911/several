from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass

from several.adapters.parser import parse_output
from several.adapters.registry import AgentSpec


@dataclass
class RunResult:
    agent: str
    status: str
    exit_code: int | None
    output: str
    duration_ms: int
    command: list[str]
    workspace: str | None = None
    tokens_used: int | None = None
    progress_percent: int | None = None
    tool_calls: list[str] | None = None


def run_agent_prompt(
    agent: AgentSpec, prompt: str, timeout: int, cwd: str | None = None
) -> RunResult:
    command = agent.build_command(prompt)
    env = None
    if agent.env:
        env = dict(os.environ)
        env.update(agent.env)

    start = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            env=env,
            cwd=cwd,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        status = "completed" if completed.returncode == 0 else "failed"
        parsed = parse_output(agent.parser_profile, completed.stdout)
        return RunResult(
            agent=agent.name,
            status=status,
            exit_code=completed.returncode,
            output=completed.stdout,
            duration_ms=duration_ms,
            command=command,
            workspace=cwd,
            tokens_used=parsed.tokens_used,
            progress_percent=parsed.progress_percent,
            tool_calls=parsed.tool_calls,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        partial = exc.stdout or ""
        return RunResult(
            agent=agent.name,
            status="timeout",
            exit_code=None,
            output=partial,
            duration_ms=duration_ms,
            command=command,
            workspace=cwd,
            tokens_used=None,
            progress_percent=None,
            tool_calls=[],
        )
    except FileNotFoundError:
        duration_ms = int((time.monotonic() - start) * 1000)
        return RunResult(
            agent=agent.name,
            status="not_found",
            exit_code=127,
            output=f"Executable not found: {command[0]}",
            duration_ms=duration_ms,
            command=command,
            workspace=cwd,
            tokens_used=None,
            progress_percent=None,
            tool_calls=[],
        )
    except Exception as exc:  # defensive path for external process issues
        duration_ms = int((time.monotonic() - start) * 1000)
        return RunResult(
            agent=agent.name,
            status="error",
            exit_code=1,
            output=f"{type(exc).__name__}: {exc}",
            duration_ms=duration_ms,
            command=command,
            workspace=cwd,
            tokens_used=None,
            progress_percent=None,
            tool_calls=[],
        )
