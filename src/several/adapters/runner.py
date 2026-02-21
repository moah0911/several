from __future__ import annotations

import os
import queue
import subprocess
import threading
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
        out_queue: queue.Queue[str | None] = queue.Queue()

        def pump_stdout() -> None:
            if process.stdout is None:
                out_queue.put(None)
                return
            for line in process.stdout:
                out_queue.put(line)
            out_queue.put(None)

        thread = threading.Thread(target=pump_stdout, daemon=True)
        thread.start()

        deadline = start + timeout
        timed_out = False

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break

            try:
                item = out_queue.get(timeout=min(0.1, max(remaining, 0.01)))
            except queue.Empty:
                if process.poll() is not None:
                    break
                continue

            if item is None:
                break

            chunks.append(item)
            if on_output is not None:
                on_output(item)

        if timed_out:
            process.kill()

        # Drain any queued output produced before shutdown.
        while True:
            try:
                item = out_queue.get_nowait()
            except queue.Empty:
                break
            if item is None:
                continue
            chunks.append(item)
            if on_output is not None:
                on_output(item)

        if process.poll() is None:
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)

        duration_ms = int((time.monotonic() - start) * 1000)
        output = "".join(chunks)

        if timed_out:
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

        return_code = process.returncode
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
