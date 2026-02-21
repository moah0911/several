from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from several.core.workspace import cleanup_workspace, create_agent_workspace, is_git_repository


def _git_available() -> bool:
    return shutil.which("git") is not None


def test_workspace_falls_back_when_not_git(tmp_path: Path) -> None:
    ws = create_agent_workspace(tmp_path / "data", tmp_path, "sess-x", "task-x", "agent")
    assert ws.managed is False
    assert ws.path == tmp_path


def test_workspace_git_worktree_lifecycle(tmp_path: Path) -> None:
    if not _git_available():
        return

    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True)

    assert is_git_repository(repo) is True

    ws = create_agent_workspace(tmp_path / "data", repo, "sess-a", "task-a", "codex")
    assert ws.managed is True
    assert ws.path.exists()
    assert (ws.path / "README.md").exists()

    cleanup_workspace(repo, ws)
    assert not ws.path.exists()
