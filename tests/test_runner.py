from __future__ import annotations

from several.adapters.registry import AgentSpec
from several.adapters.runner import run_agent_prompt


def test_runner_timeout_without_output() -> None:
    agent = AgentSpec(name="sleepy", command=["python3", "-c", "import time; time.sleep(2)"])
    result = run_agent_prompt(agent, prompt="x", timeout=1)
    assert result.status == "timeout"


def test_runner_streams_output_lines() -> None:
    agent = AgentSpec(
        name="streamer",
        command=["python3", "-c", "print('first', flush=True); print('second', flush=True)"],
    )
    seen: list[str] = []

    def on_output(line: str) -> None:
        seen.append(line.strip())

    result = run_agent_prompt(agent, prompt="x", timeout=2, on_output=on_output)
    assert result.status == "completed"
    assert "first" in seen
    assert "second" in seen
