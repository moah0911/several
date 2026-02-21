from __future__ import annotations

import concurrent.futures
import difflib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from several.adapters.registry import AgentSpec
from several.adapters.runner import RunResult, run_agent_prompt


@dataclass
class TaskExecution:
    task_id: str
    timestamp: str
    prompt: str
    mode: str
    results: list[RunResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "prompt": self.prompt,
            "mode": self.mode,
            "results": [asdict(item) for item in self.results],
        }


def execute_task(
    task_id: str,
    prompt: str,
    agents: list[AgentSpec],
    sequential: bool,
    timeout: int,
    workspaces: dict[str, str] | None = None,
    reporter: Callable[[dict[str, Any]], None] | None = None,
) -> TaskExecution:
    workspaces = workspaces or {}
    if sequential:
        results: list[RunResult] = []
        running_prompt = prompt
        for agent in agents:
            if reporter is not None:
                reporter({"type": "start", "agent": agent.name, "progress": 1})
            result = run_agent_prompt(
                agent, running_prompt, timeout, cwd=workspaces.get(agent.name)
            )
            results.append(result)
            if reporter is not None:
                reporter(
                    {
                        "type": "result",
                        "agent": result.agent,
                        "status": result.status,
                        "progress": 100,
                        "duration_ms": result.duration_ms,
                    }
                )
            running_prompt = result.output.strip() or running_prompt
        return TaskExecution(
            task_id=task_id,
            timestamp=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            prompt=prompt,
            mode="sequential",
            results=results,
        )

    results_parallel: list[RunResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(agents))) as executor:
        if reporter is not None:
            for agent in agents:
                reporter({"type": "start", "agent": agent.name, "progress": 1})
        future_map = {
            executor.submit(
                run_agent_prompt,
                agent,
                prompt,
                timeout,
                workspaces.get(agent.name),
            ): agent.name
            for agent in agents
        }
        for future in concurrent.futures.as_completed(future_map):
            result = future.result()
            results_parallel.append(result)
            if reporter is not None:
                reporter(
                    {
                        "type": "result",
                        "agent": result.agent,
                        "status": result.status,
                        "progress": 100,
                        "duration_ms": result.duration_ms,
                    }
                )

    results_parallel.sort(key=lambda item: item.agent)
    return TaskExecution(
        task_id=task_id,
        timestamp=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        prompt=prompt,
        mode="parallel",
        results=results_parallel,
    )


def format_output(payload: TaskExecution, output_format: str, compare: bool) -> str:
    if output_format == "json":
        output = json.dumps(payload.to_dict(), indent=2)
    elif output_format == "raw":
        chunks = []
        for result in payload.results:
            chunks.append(result.output.rstrip())
        output = "\n\n".join(chunks)
    else:
        lines: list[str] = [
            f"# Task {payload.task_id}",
            "",
            f"Prompt: {payload.prompt}",
            f"Mode: {payload.mode}",
            "",
        ]
        for result in payload.results:
            lines.append(f"## {result.agent}")
            lines.append(
                f"Status: {result.status} | Exit: {result.exit_code} | Duration: {result.duration_ms}ms"
            )
            lines.append(
                "Metrics: "
                f"tokens={result.tokens_used} "
                f"progress={result.progress_percent} "
                f"workspace={result.workspace}"
            )
            if result.tool_calls:
                lines.append(f"Tool calls: {', '.join(result.tool_calls)}")
            lines.append("")
            lines.append("```")
            lines.append(result.output.strip())
            lines.append("```")
            lines.append("")
        output = "\n".join(lines)

    if compare and len(payload.results) >= 2:
        output += "\n\n" + build_compare(payload.results)

    return output


def build_compare(results: list[RunResult]) -> str:
    base = results[0]
    lines: list[str] = ["## Compare", ""]
    for candidate in results[1:]:
        diff = difflib.unified_diff(
            base.output.splitlines(),
            candidate.output.splitlines(),
            fromfile=base.agent,
            tofile=candidate.agent,
            lineterm="",
        )
        lines.append(f"### {base.agent} vs {candidate.agent}")
        lines.append("```")
        diff_lines = list(diff)
        lines.extend(diff_lines[:400] if diff_lines else ["(no diff)"])
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def save_output(path: Path, content: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    output_file = path / "task-output.txt"
    output_file.write_text(content, encoding="utf-8")
    return output_file
