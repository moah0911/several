from __future__ import annotations

from several.adapters.registry import AgentSpec
from several.core.task import execute_task


def test_reporter_exceptions_do_not_break_task_execution() -> None:
    agents = [AgentSpec(name="ok", command=["python3", "-c", "print('done')"])]

    def broken_reporter(event):  # noqa: ANN001
        if event.get("type") == "output":
            raise RuntimeError("reporter failure")

    result = execute_task(
        task_id="task-x",
        prompt="p",
        agents=agents,
        sequential=False,
        timeout=5,
        reporter=broken_reporter,
    )
    assert result.results[0].status == "completed"
