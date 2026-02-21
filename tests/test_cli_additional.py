from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import several.tui.app as tui_app
from several.cli import app

runner = CliRunner()


def invoke(*args: str):
    return runner.invoke(app, list(args))


def _seed_session(cfg: Path, data: Path) -> str:
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
    task_result = invoke("-c", str(cfg), "-d", str(data), "task", "-a", "echoer", "seed")
    assert task_result.exit_code == 0
    sessions = invoke("-c", str(cfg), "-d", str(data), "sessions", "list", "--format", "json")
    assert sessions.exit_code == 0
    return json.loads(sessions.stdout)[0]["id"]


def test_sessions_export_import_delete(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    data = tmp_path / "data"
    session_id = _seed_session(cfg, data)

    export_file = tmp_path / "export.json"
    export_result = invoke(
        "-c",
        str(cfg),
        "-d",
        str(data),
        "sessions",
        "export",
        session_id,
        "-f",
        "json",
        "-o",
        str(export_file),
    )
    assert export_result.exit_code == 0
    assert export_file.exists()

    delete_result = invoke(
        "-c", str(cfg), "-d", str(data), "sessions", "delete", session_id, "--force"
    )
    assert delete_result.exit_code == 0

    import_result = invoke("-c", str(cfg), "-d", str(data), "sessions", "import", str(export_file))
    assert import_result.exit_code == 0


def test_agents_test_and_list_yaml(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    data = tmp_path / "data"
    _ = _seed_session(cfg, data)

    test_result = invoke(
        "-c", str(cfg), "-d", str(data), "agents", "test", "echoer", "--prompt", "hello"
    )
    assert test_result.exit_code == 0
    payload = json.loads(test_result.stdout)
    assert payload["status"] in {"completed", "failed"}

    list_yaml = invoke("-c", str(cfg), "-d", str(data), "agents", "list", "--format", "yaml")
    assert list_yaml.exit_code == 0
    assert "echoer" in list_yaml.stdout


def test_config_reset_and_missing_logs(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    data = tmp_path / "data"

    logs_result = invoke("-c", str(cfg), "-d", str(data), "logs")
    assert logs_result.exit_code == 0
    assert "No logs found" in logs_result.stdout

    set_result = invoke("-c", str(cfg), "-d", str(data), "config", "set", "ui.layout", "vertical")
    assert set_result.exit_code == 0

    reset_result = invoke("-c", str(cfg), "-d", str(data), "config", "reset", "--force")
    assert reset_result.exit_code == 0

    get_result = invoke("-c", str(cfg), "-d", str(data), "config", "get", "ui.layout")
    assert get_result.exit_code == 0
    assert "grid" in get_result.stdout


def test_run_invalid_session_fails(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "cfg"
    data = tmp_path / "data"

    class DummyApp:
        def __init__(self, active_agents, layout, task_submitter):  # noqa: ANN001
            self.active_agents = active_agents
            self.layout = layout
            self.task_submitter = task_submitter

        def run(self):  # noqa: ANN201
            return None

    monkeypatch.setattr(tui_app, "SeveralApp", DummyApp)
    run_result = invoke("-c", str(cfg), "-d", str(data), "run", "-s", "sess-missing")
    assert run_result.exit_code != 0
