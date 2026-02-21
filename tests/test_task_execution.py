from __future__ import annotations

from several.adapters.registry import AgentSpec
from several.core.task import execute_task


def test_execute_task_parallel() -> None:
    agents = [
        AgentSpec(name="a1", command=["python3", "-c", "print('one')"]),
        AgentSpec(name="a2", command=["python3", "-c", "print('two')"]),
    ]
    result = execute_task("task-1", "ignored", agents, sequential=False, timeout=5)
    assert result.mode == "parallel"
    assert len(result.results) == 2
    assert all(item.status == "completed" for item in result.results)


def test_execute_task_sequential() -> None:
    agents = [
        AgentSpec(name="s1", command=["python3", "-c", "print('first')"]),
        AgentSpec(name="s2", command=["python3", "-c", "print('second')"]),
    ]
    result = execute_task("task-2", "prompt", agents, sequential=True, timeout=5)
    assert result.mode == "sequential"
    assert len(result.results) == 2


def test_execute_task_reports_output_events() -> None:
    agents = [AgentSpec(name="evt", command=["python3", "-c", "print('line-a')\nprint('line-b')"])]
    events: list[dict[str, object]] = []

    def reporter(event: dict[str, object]) -> None:
        events.append(event)

    result = execute_task(
        "task-3", "prompt", agents, sequential=False, timeout=5, reporter=reporter
    )
    assert len(result.results) == 1
    assert any(evt.get("type") == "output" for evt in events)
    assert any(evt.get("type") == "result" for evt in events)
