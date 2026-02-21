from __future__ import annotations

import tempfile
from pathlib import Path

from several.core.config import get_key, load_config, save_config, set_key
from several.core.db import StateStore, TaskResultRecord
from several.core.paths import ensure_directories, resolve_paths


def test_paths_resolve_and_ensure_directories() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = resolve_paths(config_dir=str(root / "cfg"), data_dir=str(root / "data"))
        ensure_directories(paths)
        assert paths.config_dir.exists()
        assert paths.data_dir.exists()
        assert paths.agents_dir.exists()
        assert paths.logs_dir.exists()


def test_config_get_set_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        config_file = Path(tmp) / "config.yaml"
        config = load_config(config_file)
        set_key(config, "ui.layout", "horizontal")
        save_config(config_file, config)

        loaded = load_config(config_file)
        assert get_key(loaded, "ui.layout") == "horizontal"


def test_state_store_session_task_export() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = StateStore(Path(tmp) / "several.db")
        session_id = store.create_session(["codex", "claude"], layout="grid")
        task_id = store.create_task(session_id, "test prompt", "parallel")
        store.add_task_result(
            task_id,
            TaskResultRecord(
                agent="codex",
                status="completed",
                exit_code=0,
                duration_ms=10,
                output="ok",
            ),
        )
        store.close_session(session_id)

        sessions = store.list_sessions()
        assert any(item["id"] == session_id for item in sessions)

        export = store.export_session(session_id)
        assert export["session"]["id"] == session_id
        assert export["tasks"][0]["id"] == task_id
