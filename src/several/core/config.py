from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG: dict[str, Any] = {
    "ui": {
        "theme": "dark",
        "layout": "grid",
        "refresh_rate": 30,
        "animations": True,
        "compact_mode": False,
    },
    "agents": {
        "auto_detect": True,
        "detect_on_startup": True,
        "default_agents": [],
        "extra_paths": [],
        "timeout": 300,
    },
    "performance": {
        "max_concurrent_agents": 8,
        "buffer_size": 65536,
        "default_timeout": 300,
    },
    "storage": {
        "max_session_age_days": 30,
        "max_log_age_days": 7,
        "compress_logs": True,
        "workspace_cleanup": "on_exit",
    },
    "logging": {
        "level": "info",
        "format": "text",
        "max_size": 100,
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return copy.deepcopy(DEFAULT_CONFIG)
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Invalid config at {path}: expected mapping")
    return deep_merge(DEFAULT_CONFIG, loaded)


def save_config(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)


def reset_config(path: Path) -> None:
    save_config(path, copy.deepcopy(DEFAULT_CONFIG))


def _coerce_value(raw: str) -> Any:
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def get_key(config: dict[str, Any], key: str) -> Any:
    current: Any = config
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"Unknown config key: {key}")
        current = current[part]
    return current


def set_key(config: dict[str, Any], key: str, raw_value: str) -> None:
    parts = key.split(".")
    current: Any = config
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = _coerce_value(raw_value)


def edit_config(path: Path) -> int:
    editor = os.environ.get("EDITOR", "vi")
    return subprocess.call([editor, str(path)])
