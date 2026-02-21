from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WorkspaceInfo:
    agent: str
    path: Path
    managed: bool


def is_git_repository(cwd: Path) -> bool:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(cwd),
            capture_output=True,
            check=False,
            text=True,
            timeout=2,
        )
        return completed.returncode == 0 and completed.stdout.strip() == "true"
    except Exception:
        return False


def create_agent_workspace(
    root_data_dir: Path,
    cwd: Path,
    session_id: str,
    task_id: str,
    agent: str,
) -> WorkspaceInfo:
    if not is_git_repository(cwd):
        return WorkspaceInfo(agent=agent, path=cwd, managed=False)

    ws_root = root_data_dir / "workspaces" / session_id / task_id
    ws_root.mkdir(parents=True, exist_ok=True)
    ws_path = ws_root / agent

    subprocess.run(
        ["git", "worktree", "add", "--detach", str(ws_path)],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )
    return WorkspaceInfo(agent=agent, path=ws_path, managed=True)


def cleanup_workspace(cwd: Path, workspace: WorkspaceInfo) -> None:
    if not workspace.managed:
        return

    subprocess.run(
        ["git", "worktree", "remove", "--force", str(workspace.path)],
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
    )
    if workspace.path.exists():
        shutil.rmtree(workspace.path, ignore_errors=True)


def cleanup_session_workspaces(cwd: Path, root_data_dir: Path, session_id: str) -> None:
    base = root_data_dir / "workspaces" / session_id
    if not base.exists():
        return
    for child in base.rglob("*"):
        if child.is_dir():
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(child)],
                cwd=str(cwd),
                check=False,
                capture_output=True,
                text=True,
            )
    shutil.rmtree(base, ignore_errors=True)
