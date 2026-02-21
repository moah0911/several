from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    config_dir: Path
    data_dir: Path
    logs_dir: Path
    agents_dir: Path
    db_path: Path
    config_file: Path
    log_file: Path


def _default_root() -> Path:
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data) / "several"
    return Path.home() / ".local" / "share" / "several"


def resolve_paths(config_dir: str | None = None, data_dir: str | None = None) -> RuntimePaths:
    env_config = os.environ.get("SEVERAL_CONFIG_DIR")
    env_data = os.environ.get("SEVERAL_DATA_DIR")

    base_root = _default_root()
    resolved_config = Path(config_dir or env_config or (base_root / "config"))
    resolved_data = Path(data_dir or env_data or (base_root / "data"))

    logs_dir = resolved_data / "logs"
    agents_dir = resolved_config / "agents"
    db_path = resolved_data / "several.db"
    config_file = resolved_config / "config.yaml"
    log_file = logs_dir / "several.log"

    return RuntimePaths(
        config_dir=resolved_config,
        data_dir=resolved_data,
        logs_dir=logs_dir,
        agents_dir=agents_dir,
        db_path=db_path,
        config_file=config_file,
        log_file=log_file,
    )


def ensure_directories(paths: RuntimePaths) -> None:
    for directory in (paths.config_dir, paths.data_dir, paths.logs_dir, paths.agents_dir):
        directory.mkdir(parents=True, exist_ok=True)
