from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import several.tui.app as tui_app
from several.cli import app

runner = CliRunner()


def invoke(*args: str):
    return runner.invoke(app, list(args))


def test_version_flag() -> None:
    result = invoke("--version")
    assert result.exit_code == 0
    assert "several 0.1.0" in result.stdout


def test_config_set_and_get(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    data = tmp_path / "data"

    set_result = invoke("-c", str(cfg), "-d", str(data), "config", "set", "ui.layout", "horizontal")
    assert set_result.exit_code == 0

    get_result = invoke("-c", str(cfg), "-d", str(data), "config", "get", "ui.layout")
    assert get_result.exit_code == 0
    assert "horizontal" in get_result.stdout


def test_agents_add_list_remove_and_task(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    data = tmp_path / "data"

    add_result = invoke(
        "-c",
        str(cfg),
        "-d",
        str(data),
        "agents",
        "add",
        "echoer",
        "--command",
        "/usr/bin/echo",
        "--args",
        "{prompt}",
    )
    assert add_result.exit_code == 0

    list_result = invoke("-c", str(cfg), "-d", str(data), "agents", "list", "--format", "json")
    assert list_result.exit_code == 0
    payload = json.loads(list_result.stdout)
    assert any(item["name"] == "echoer" for item in payload)

    task_result = invoke(
        "-c",
        str(cfg),
        "-d",
        str(data),
        "task",
        "-a",
        "echoer",
        "-o",
        "json",
        "hello world",
    )
    assert task_result.exit_code == 0
    task_payload = json.loads(task_result.stdout)
    assert task_payload["prompt"] == "hello world"
    assert task_payload["results"][0]["status"] == "completed"

    sessions_result = invoke(
        "-c", str(cfg), "-d", str(data), "sessions", "list", "--format", "json"
    )
    assert sessions_result.exit_code == 0
    session_id = json.loads(sessions_result.stdout)[0]["id"]

    tail_result = invoke(
        "-c", str(cfg), "-d", str(data), "sessions", "tail", session_id, "--limit", "50"
    )
    assert tail_result.exit_code == 0
    assert "[output]" in tail_result.stdout or "[result]" in tail_result.stdout

    logs_result = invoke("-c", str(cfg), "-d", str(data), "logs")
    assert logs_result.exit_code == 0
    assert "task started" in logs_result.stdout

    remove_result = invoke("-c", str(cfg), "-d", str(data), "agents", "remove", "echoer")
    assert remove_result.exit_code == 0


def test_run_resumes_existing_session(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "cfg"
    data = tmp_path / "data"

    add_result = invoke(
        "-c",
        str(cfg),
        "-d",
        str(data),
        "agents",
        "add",
        "echoer",
        "--command",
        "/usr/bin/echo",
        "--args",
        "{prompt}",
    )
    assert add_result.exit_code == 0

    task_result = invoke(
        "-c",
        str(cfg),
        "-d",
        str(data),
        "task",
        "-a",
        "echoer",
        "seed session",
    )
    assert task_result.exit_code == 0

    sessions_result = invoke(
        "-c", str(cfg), "-d", str(data), "sessions", "list", "--format", "json"
    )
    assert sessions_result.exit_code == 0
    sessions = json.loads(sessions_result.stdout)
    assert sessions
    session_id = sessions[0]["id"]

    class DummyApp:
        def __init__(self, active_agents, layout, task_submitter):  # noqa: ANN001
            self.active_agents = active_agents
            self.layout = layout
            self.task_submitter = task_submitter

        def run(self):  # noqa: ANN201
            return None

    monkeypatch.setattr(tui_app, "SeveralApp", DummyApp)
    run_result = invoke("-c", str(cfg), "-d", str(data), "run", "-s", session_id)
    assert run_result.exit_code == 0
    assert f"Session: {session_id}" in run_result.stdout
