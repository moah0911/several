from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AgentSpec:
    name: str
    command: list[str]
    kind: str = "official"
    path: str | None = None
    version: str | None = None
    installed: bool = False
    env: dict[str, str] = field(default_factory=dict)
    parser_profile: str | None = None

    def build_command(self, prompt: str) -> list[str]:
        result: list[str] = []
        for token in self.command:
            result.append(token.replace("{prompt}", prompt))
        return result


def builtin_agent_specs() -> dict[str, AgentSpec]:
    return {
        "claude": AgentSpec(
            name="claude",
            command=["claude", "-p", "{prompt}"],
            parser_profile="claude",
        ),
        "codex": AgentSpec(
            name="codex",
            command=["codex", "exec", "{prompt}"],
            parser_profile="codex",
        ),
        "gemini": AgentSpec(
            name="gemini",
            command=["gemini", "-p", "{prompt}"],
            parser_profile="gemini",
        ),
        "qwen": AgentSpec(
            name="qwen",
            command=["qwen", "-p", "{prompt}"],
            parser_profile="qwen",
        ),
    }


def _detect_version(binary: str) -> str | None:
    for args in ([binary, "--version"], [binary, "version"]):
        try:
            output = subprocess.check_output(args, stderr=subprocess.STDOUT, timeout=2, text=True)
            line = output.strip().splitlines()[0] if output.strip() else "unknown"
            return line[:120]
        except Exception:
            continue
    return None


def _load_custom_agent(path: Path) -> AgentSpec | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except Exception:
        return None

    if not isinstance(data, dict) or "name" not in data:
        return None

    command_data = data.get("command", {})
    binary = command_data.get("binary")
    args = command_data.get("args", [])
    if not binary:
        return None

    tokens = [str(binary)] + [str(item) for item in args]
    env = data.get("env", {})
    if not isinstance(env, dict):
        env = {}

    return AgentSpec(
        name=str(data["name"]),
        command=tokens,
        kind="custom",
        env={str(k): str(v) for k, v in env.items()},
        parser_profile=str(data.get("parsing", {}).get("profile", "generic")),
    )


def discover_agents(agents_dir: Path, include_available: bool = True) -> dict[str, AgentSpec]:
    specs = builtin_agent_specs()

    if agents_dir.exists():
        for file in agents_dir.glob("*.yaml"):
            custom = _load_custom_agent(file)
            if custom:
                specs[custom.name] = custom

    discovered: dict[str, AgentSpec] = {}
    for name, spec in specs.items():
        binary = spec.command[0]
        path = shutil.which(binary)
        if path:
            spec.installed = True
            spec.path = path
            spec.version = _detect_version(binary)
            discovered[name] = spec
        elif include_available:
            discovered[name] = spec

    return discovered


def save_custom_agent(
    agents_dir: Path,
    name: str,
    command_path: str,
    args: list[str],
    env_pairs: dict[str, str],
    parser: str | None,
    detect_version: str | None,
) -> Path:
    agents_dir.mkdir(parents=True, exist_ok=True)
    out_path = agents_dir / f"{name}.yaml"

    payload: dict[str, Any] = {
        "name": name,
        "command": {
            "binary": command_path,
            "args": args,
        },
        "env": env_pairs,
    }
    if parser:
        payload["parsing"] = {"profile": parser}
    if detect_version:
        payload["detection"] = {"command": detect_version}

    with out_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)

    return out_path


def remove_custom_agent(agents_dir: Path, name: str) -> bool:
    target = agents_dir / f"{name}.yaml"
    if target.exists():
        target.unlink()
        return True
    return False


def parse_env_pairs(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    env: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        env[key] = os.path.expandvars(value)
    return env
