from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from typing import Callable

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
    agent: AgentSpec,
    prompt: str,
    timeout: int,
    cwd: str | None = None,
    on_output: Callable[[str], None] | None = None,
) -> RunResult:
    command = agent.build_command(prompt)
    env = dict(os.environ)
    if agent.env:
        env.update(agent.env)

    start = time.monotonic()
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=cwd,
        )
        chunks: list[str] = []
        while True:
            if process.stdout is None:
                break
            line = process.stdout.readline()
            if line:
                chunks.append(line)
                if on_output is not None:
                    on_output(line)
            else:
                if process.poll() is not None:
                    break
                if (time.monotonic() - start) > timeout:
                    process.kill()
                    remaining = process.stdout.read() if process.stdout else ""
                    if remaining:
                        chunks.append(remaining)
                        if on_output is not None:
                            on_output(remaining)
                    duration_ms = int((time.monotonic() - start) * 1000)
                    output = "".join(chunks)
                    return RunResult(
                        agent=agent.name,
                        status="timeout",
                        exit_code=None,
                        output=output,
                        duration_ms=duration_ms,
                        command=command,
                        workspace=cwd,
                        tokens_used=None,
                        progress_percent=None,
                        tool_calls=[],
                    )
                time.sleep(0.01)

        return_code = process.wait(timeout=1)
        duration_ms = int((time.monotonic() - start) * 1000)
        output = "".join(chunks)
        status = "completed" if return_code == 0 else "failed"
        parsed = parse_output(agent.parser_profile, output)
        return RunResult(
            agent=agent.name,
            status=status,
            exit_code=return_code,
            output=output,
            duration_ms=duration_ms,
            command=command,
            workspace=cwd,
            tokens_used=parsed.tokens_used,
            progress_percent=parsed.progress_percent,
            tool_calls=parsed.tool_calls,
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
