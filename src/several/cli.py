from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import click
import typer
import yaml
from rich.console import Console
from rich.table import Table

from several.adapters.registry import (
    AgentSpec,
    discover_agents,
    parse_env_pairs,
    remove_custom_agent,
    save_custom_agent,
)
from several.adapters.runner import run_agent_prompt
from several.core.config import (
    edit_config,
    get_key,
    load_config,
    reset_config,
    save_config,
    set_key,
)
from several.core.db import StateStore, TaskResultRecord
from several.core.logging import write_log
from several.core.paths import RuntimePaths, ensure_directories, resolve_paths
from several.core.task import execute_task, format_output
from several.core.workspace import WorkspaceInfo, cleanup_workspace, create_agent_workspace

app = typer.Typer(
    name="several",
    add_completion=False,
    no_args_is_help=False,
    help="Universal AI Agent Orchestrator",
)
agents_app = typer.Typer(help="Manage available AI agents")
sessions_app = typer.Typer(help="Manage sessions")
config_app = typer.Typer(help="Manage configuration")
app.add_typer(agents_app, name="agents")
app.add_typer(sessions_app, name="sessions")
app.add_typer(config_app, name="config")

console = Console()


@dataclass
class AppContext:
    paths: RuntimePaths
    config: dict[str, Any]
    verbose: int
    quiet: bool


def _split_agents(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _ctx() -> AppContext:
    ctx = click.get_current_context().obj
    if not isinstance(ctx, AppContext):
        raise typer.BadParameter("Application context not initialized")
    return ctx


def _load_agent_specs(ctx: AppContext, requested: list[str], auto_detect: bool) -> list[AgentSpec]:
    detected = discover_agents(ctx.paths.agents_dir, include_available=not auto_detect)

    if requested:
        missing = [name for name in requested if name not in detected]
        if missing:
            raise typer.BadParameter(f"Unknown agents: {', '.join(missing)}")
        return [detected[name] for name in requested]

    if auto_detect:
        installed = [spec for spec in detected.values() if spec.installed]
        if installed:
            return sorted(installed, key=lambda item: item.name)

    # fallback to all known specs
    return sorted(detected.values(), key=lambda item: item.name)


def _execute_task_for_session(
    ctx: AppContext,
    store: StateStore,
    session_id: str,
    prompt: str,
    selected: list[AgentSpec],
    sequential: bool,
    timeout: int,
    output_format: str,
    compare: bool,
    close_session: bool,
    reporter: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[Any, str]:
    selected_names = [item.name for item in selected]
    mode = "sequential" if sequential else "parallel"
    task_id = store.create_task(session_id, prompt, mode)
    write_log(
        ctx.paths.log_file,
        "info",
        "task started",
        task_id=task_id,
        session_id=session_id,
        mode=mode,
        agents=selected_names,
    )

    cwd = Path.cwd()
    cleanup_mode = str(ctx.config.get("storage", {}).get("workspace_cleanup", "on_exit"))
    workspaces: dict[str, WorkspaceInfo] = {}

    def emit_event(event: dict[str, Any]) -> None:
        event_type = str(event.get("type", "event"))
        event_agent = event.get("agent")
        try:
            store.add_task_event(
                task_id=task_id,
                event_type=event_type,
                payload=event,
                agent=str(event_agent) if event_agent is not None else None,
            )
        except Exception as exc:
            write_log(
                ctx.paths.log_file,
                "warning",
                "task event persistence failed",
                task_id=task_id,
                event_type=event_type,
                error=f"{type(exc).__name__}: {exc}",
            )
        if reporter is not None:
            reporter(event)

    for spec in selected:
        try:
            ws = create_agent_workspace(ctx.paths.data_dir, cwd, session_id, task_id, spec.name)
        except Exception as exc:
            write_log(
                ctx.paths.log_file,
                "warning",
                "workspace creation failed; using current directory",
                agent=spec.name,
                error=f"{type(exc).__name__}: {exc}",
            )
            ws = WorkspaceInfo(agent=spec.name, path=cwd, managed=False)
        workspaces[spec.name] = ws
        write_log(
            ctx.paths.log_file,
            "info",
            "workspace assigned",
            task_id=task_id,
            agent=spec.name,
            path=str(ws.path),
            managed=ws.managed,
        )
        emit_event(
            {
                "type": "workspace",
                "agent": spec.name,
                "workspace": str(ws.path),
                "managed": ws.managed,
            }
        )

    execution = execute_task(
        task_id=task_id,
        prompt=prompt,
        agents=selected,
        sequential=sequential,
        timeout=timeout,
        workspaces={name: str(info.path) for name, info in workspaces.items()},
        reporter=emit_event,
    )

    for result in execution.results:
        store.add_task_result(
            task_id,
            TaskResultRecord(
                agent=result.agent,
                status=result.status,
                exit_code=result.exit_code,
                duration_ms=result.duration_ms,
                output=result.output,
                workspace=result.workspace,
                tokens_used=result.tokens_used,
                progress_percent=result.progress_percent,
                tool_calls=result.tool_calls,
            ),
        )
        write_log(
            ctx.paths.log_file,
            "info",
            "task result",
            task_id=task_id,
            agent=result.agent,
            status=result.status,
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            workspace=result.workspace,
            tokens_used=result.tokens_used,
            progress_percent=result.progress_percent,
            tool_calls=result.tool_calls,
        )

    if close_session:
        store.close_session(session_id)
    write_log(ctx.paths.log_file, "info", "task completed", task_id=task_id, session_id=session_id)

    if cleanup_mode in {"immediate", "on_exit"}:
        for info in workspaces.values():
            cleanup_workspace(cwd, info)
            write_log(
                ctx.paths.log_file,
                "info",
                "workspace cleaned",
                task_id=task_id,
                agent=info.agent,
                path=str(info.path),
                mode=cleanup_mode,
            )

    rendered = format_output(execution, output_format=output_format, compare=compare)
    return execution, rendered


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    config_dir: str | None = typer.Option(None, "--config", "-c", help="Config directory"),
    data_dir: str | None = typer.Option(None, "--data-dir", "-d", help="Data directory"),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True, help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-error output"),
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit"),
) -> None:
    if version:
        console.print("several 0.1.0")
        raise typer.Exit(code=0)

    paths = resolve_paths(config_dir, data_dir)
    ensure_directories(paths)
    config = load_config(paths.config_file)
    ctx.obj = AppContext(paths=paths, config=config, verbose=verbose, quiet=quiet)

    if ctx.invoked_subcommand is None:
        run_command()


@app.command("run")
def run_command(
    agents: str | None = typer.Option(None, "--agents", "-a", help="Comma-separated agents"),
    session: str | None = typer.Option(None, "--session", "-s", help="Resume session"),
    layout: str | None = typer.Option(None, "--layout", "-l", help="grid|horizontal|vertical"),
    no_auto_detect: bool = typer.Option(
        False, "--no-auto-detect", help="Disable automatic discovery"
    ),
) -> None:
    ctx = _ctx()
    store = StateStore(ctx.paths.db_path)
    requested_agents = _split_agents(agents)

    if session:
        if not store.session_exists(session):
            raise typer.BadParameter(f"Session not found: {session}")
        saved = store.get_session(session)
        resume_agents = requested_agents or list(saved.get("agents", []))
        selected = _load_agent_specs(
            ctx,
            resume_agents,
            auto_detect=not no_auto_detect and not bool(requested_agents),
        )
        session_id = session
        session_layout = layout or str(saved.get("layout", "grid"))
    else:
        selected = _load_agent_specs(ctx, requested_agents, auto_detect=not no_auto_detect)
        session_layout = layout or str(ctx.config.get("ui", {}).get("layout", "grid"))
        session_id = store.create_session([item.name for item in selected], layout=session_layout)

    selected_names = [item.name for item in selected]
    write_log(
        ctx.paths.log_file,
        "info",
        "run command",
        session_id=session_id,
        agents=selected_names,
        resumed=bool(session),
    )

    console.print(f"Session: {session_id}")
    console.print(f"Agents: {', '.join(selected_names) if selected_names else '(none)'}")

    try:
        from several.tui.app import SeveralApp
    except Exception as exc:
        console.print(
            f"TUI unavailable ({type(exc).__name__}). Install dependencies and run again.\n"
            'You can still use CLI mode with: several task "..."'
        )
        return

    timeout = int(ctx.config.get("performance", {}).get("default_timeout", 300))

    def submit_task(
        prompt_text: str, reporter: Callable[[dict[str, Any]], None] | None = None
    ) -> str:
        _, rendered_text = _execute_task_for_session(
            ctx=ctx,
            store=store,
            session_id=session_id,
            prompt=prompt_text,
            selected=selected,
            sequential=False,
            timeout=timeout,
            output_format="markdown",
            compare=False,
            close_session=False,
            reporter=reporter,
        )
        return rendered_text

    app_instance = SeveralApp(
        active_agents=selected_names,
        layout=session_layout,
        task_submitter=submit_task,
    )
    try:
        app_instance.run()
    finally:
        store.close_session(session_id)
        write_log(ctx.paths.log_file, "info", "run session closed", session_id=session_id)


@app.command("task")
def task_command(
    prompt: str = typer.Argument(..., help="Task prompt"),
    agents: str | None = typer.Option(None, "--agents", "-a", help="Comma-separated agents"),
    parallel: bool = typer.Option(True, "--parallel", "-p", help="Run in parallel"),
    sequential: bool = typer.Option(False, "--sequential", help="Run sequentially"),
    output: str = typer.Option("markdown", "--output", "-o", help="json|markdown|raw"),
    save: Path | None = typer.Option(None, "--save", help="Save output directory"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Timeout per agent (seconds)"),
    compare: bool = typer.Option(False, "--compare", help="Show diff/compare view"),
) -> None:
    _ = parallel  # retained for CLI compatibility; sequential flag controls mode.
    ctx = _ctx()
    store = StateStore(ctx.paths.db_path)

    selected = _load_agent_specs(ctx, _split_agents(agents), auto_detect=True)
    session_id = store.create_session([item.name for item in selected])
    execution, rendered = _execute_task_for_session(
        ctx=ctx,
        store=store,
        session_id=session_id,
        prompt=prompt,
        selected=selected,
        sequential=sequential,
        timeout=timeout,
        output_format=output,
        compare=compare,
        close_session=True,
    )

    if output == "json":
        typer.echo(rendered)
    else:
        console.print(rendered)

    if save:
        save.mkdir(parents=True, exist_ok=True)
        suffix = "json" if output == "json" else "md"
        out_file = save / f"{execution.task_id}.{suffix}"
        out_file.write_text(rendered, encoding="utf-8")
        console.print(f"Saved: {out_file}")


@agents_app.command("list")
def agents_list(
    installed: bool = typer.Option(False, "--installed", help="Only installed/detected agents"),
    available: bool = typer.Option(False, "--available", help="Show all supported agents"),
    format: str = typer.Option("table", "--format", help="table|json|yaml"),
) -> None:
    ctx = _ctx()
    include_available = available or not installed
    specs = discover_agents(ctx.paths.agents_dir, include_available=include_available)

    values = sorted(specs.values(), key=lambda item: item.name)
    if installed:
        values = [item for item in values if item.installed]

    if format == "json":
        payload = [
            {
                "name": spec.name,
                "installed": spec.installed,
                "version": spec.version,
                "type": spec.kind,
                "path": spec.path,
            }
            for spec in values
        ]
        typer.echo(json.dumps(payload, indent=2))
        return

    if format == "yaml":
        payload = [
            {
                "name": spec.name,
                "installed": spec.installed,
                "version": spec.version,
                "type": spec.kind,
                "path": spec.path,
            }
            for spec in values
        ]
        typer.echo(yaml.safe_dump(payload, sort_keys=False))
        return

    table = Table(title="Agents")
    table.add_column("Agent")
    table.add_column("Status")
    table.add_column("Version")
    table.add_column("Type")
    table.add_column("Path")

    for spec in values:
        table.add_row(
            spec.name,
            "active" if spec.installed else "absent",
            spec.version or "-",
            spec.kind,
            spec.path or "Not found",
        )
    console.print(table)


@agents_app.command("add")
def agents_add(
    name: str,
    command: str = typer.Option(..., "--command", help="Path to executable"),
    args: str = typer.Option("", "--args", help="Comma-separated default args"),
    env: str | None = typer.Option(None, "--env", help="KEY=VAL,KEY2=VAL2"),
    detect_version: str | None = typer.Option(None, "--detect-version", help="Version command"),
    parser: str | None = typer.Option(None, "--parser", help="Parser profile"),
) -> None:
    ctx = _ctx()
    arg_list = [item.strip() for item in args.split(",") if item.strip()]
    env_map = parse_env_pairs(env)
    out = save_custom_agent(
        ctx.paths.agents_dir, name, command, arg_list, env_map, parser, detect_version
    )
    write_log(ctx.paths.log_file, "info", "agent added", name=name, path=str(out))
    console.print(f"Added agent config: {out}")


@agents_app.command("remove")
def agents_remove(name: str) -> None:
    ctx = _ctx()
    removed = remove_custom_agent(ctx.paths.agents_dir, name)
    if not removed:
        raise typer.BadParameter(f"Agent not found: {name}")
    write_log(ctx.paths.log_file, "info", "agent removed", name=name)
    console.print(f"Removed agent: {name}")


@agents_app.command("test")
def agents_test(
    name: str,
    prompt: str = typer.Option("Hello", "--prompt", help="Test prompt"),
    timeout: int = typer.Option(30, "--timeout", help="Timeout in seconds"),
) -> None:
    ctx = _ctx()
    specs = discover_agents(ctx.paths.agents_dir, include_available=True)
    spec = specs.get(name)
    if spec is None:
        raise typer.BadParameter(f"Agent not found: {name}")

    result = run_agent_prompt(spec, prompt=prompt, timeout=timeout)
    typer.echo(
        json.dumps(
            {
                "agent": result.agent,
                "status": result.status,
                "exit_code": result.exit_code,
                "duration_ms": result.duration_ms,
                "command": result.command,
                "output": result.output,
            },
            indent=2,
        )
    )


@sessions_app.command("list")
def sessions_list(
    active: bool = typer.Option(False, "--active", help="Only active sessions"),
    format: str = typer.Option("table", "--format", help="table|json|yaml"),
) -> None:
    ctx = _ctx()
    store = StateStore(ctx.paths.db_path)
    sessions = store.list_sessions(active_only=active)

    if format == "json":
        typer.echo(json.dumps(sessions, indent=2))
        return
    if format == "yaml":
        typer.echo(yaml.safe_dump(sessions, sort_keys=False))
        return

    table = Table(title="Sessions")
    table.add_column("Session ID")
    table.add_column("Created")
    table.add_column("Agents")
    table.add_column("Tasks")
    table.add_column("Status")
    for item in sessions:
        table.add_row(
            item["id"],
            item["created_at"],
            str(len(item.get("agents", []))),
            str(item["task_count"]),
            item["status"],
        )
    console.print(table)


def _render_markdown_export(payload: dict[str, Any]) -> str:
    session = payload["session"]
    lines = [
        "# Several Session Export",
        "",
        f"Session: {session['id']}",
        f"Created: {session['created_at']}",
        f"Status: {session['status']}",
        f"Agents: {', '.join(session.get('agents', []))}",
        "",
    ]

    for task in payload.get("tasks", []):
        lines.append(f"## Task {task['id']}")
        lines.append(task.get("prompt", ""))
        lines.append("")
        for result in task.get("results", []):
            lines.append(f"### {result.get('agent', 'unknown')}")
            lines.append(f"Status: {result.get('status')} | Exit: {result.get('exit_code')}")
            lines.append("```")
            lines.append((result.get("output") or "").strip())
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


@sessions_app.command("export")
def sessions_export(
    session_id: str,
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("markdown", "--format", "-f", help="markdown|json|html"),
) -> None:
    ctx = _ctx()
    store = StateStore(ctx.paths.db_path)
    payload = store.export_session(session_id)

    if format == "json":
        rendered = json.dumps(payload, indent=2)
    elif format == "html":
        rendered = "<pre>" + _render_markdown_export(payload) + "</pre>"
    else:
        rendered = _render_markdown_export(payload)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        console.print(f"Exported to {output}")
    else:
        if format == "json":
            typer.echo(rendered)
        else:
            console.print(rendered)


@sessions_app.command("import")
def sessions_import(file: Path) -> None:
    ctx = _ctx()
    store = StateStore(ctx.paths.db_path)

    if not file.exists():
        raise typer.BadParameter(f"File not found: {file}")

    if file.suffix.lower() == ".json":
        payload = json.loads(file.read_text(encoding="utf-8"))
    else:
        raise typer.BadParameter("Only JSON import is currently supported")

    session_id = store.import_session(payload)
    write_log(ctx.paths.log_file, "info", "session imported", session_id=session_id, file=str(file))
    console.print(f"Imported session: {session_id}")


@sessions_app.command("delete")
def sessions_delete(
    session_id: str, force: bool = typer.Option(False, "--force", help="Skip confirmation")
) -> None:
    ctx = _ctx()
    store = StateStore(ctx.paths.db_path)

    if not force:
        confirmed = typer.confirm(f"Delete session {session_id}?", default=False)
        if not confirmed:
            console.print("Canceled")
            raise typer.Exit(code=0)

    removed = store.delete_session(session_id)
    if removed == 0:
        raise typer.BadParameter(f"Session not found: {session_id}")
    write_log(ctx.paths.log_file, "info", "session deleted", session_id=session_id)
    console.print(f"Deleted session: {session_id}")


@sessions_app.command("tail")
def sessions_tail(
    session_id: str,
    task: str | None = typer.Option(None, "--task", help="Filter by task ID"),
    agent: str | None = typer.Option(None, "--agent", help="Filter by agent"),
    follow: bool = typer.Option(False, "--follow", help="Follow new events"),
    limit: int = typer.Option(200, "--limit", help="Max events per poll"),
) -> None:
    ctx = _ctx()
    store = StateStore(ctx.paths.db_path)
    if not store.session_exists(session_id):
        raise typer.BadParameter(f"Session not found: {session_id}")

    last_id: int | None = None
    while True:
        events = store.list_task_events(
            session_id=session_id,
            task_id=task,
            agent=agent,
            since_id=last_id,
            limit=limit,
        )
        for event in events:
            last_id = int(event["id"])
            payload = event["payload"]
            line = payload.get("line")
            if isinstance(line, str) and line:
                prefix = f"{event['created_at']} {event.get('agent') or '-'}[{event['event_type']}]"
                typer.echo(f"{prefix} {line}")
            else:
                typer.echo(
                    f"{event['created_at']} {event.get('agent') or '-'}[{event['event_type']}] "
                    f"{json.dumps(payload, ensure_ascii=True)}"
                )
        if not follow:
            return
        time.sleep(1)


@config_app.command("get")
def config_get(key: str) -> None:
    ctx = _ctx()
    value = get_key(ctx.config, key)
    if isinstance(value, (dict, list)):
        console.print(yaml.safe_dump(value, sort_keys=False))
    else:
        console.print(str(value))


@config_app.command("set")
def config_set(key: str, value: str) -> None:
    ctx = _ctx()
    set_key(ctx.config, key, value)
    save_config(ctx.paths.config_file, ctx.config)
    write_log(ctx.paths.log_file, "info", "config updated", key=key)
    console.print(f"Updated {key}")


@config_app.command("edit")
def config_edit() -> None:
    ctx = _ctx()
    if not ctx.paths.config_file.exists():
        save_config(ctx.paths.config_file, ctx.config)
    exit_code = edit_config(ctx.paths.config_file)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@config_app.command("reset")
def config_reset(force: bool = typer.Option(False, "--force", help="Skip confirmation")) -> None:
    ctx = _ctx()
    if not force:
        confirmed = typer.confirm("Reset configuration to defaults?", default=False)
        if not confirmed:
            console.print("Canceled")
            raise typer.Exit(code=0)
    reset_config(ctx.paths.config_file)
    write_log(ctx.paths.log_file, "info", "config reset")
    console.print("Configuration reset to defaults")


@app.command("logs")
def logs(
    follow: bool = typer.Option(False, "--follow", help="Follow output"),
    agent: str | None = typer.Option(None, "--agent", help="Filter by agent name"),
    since: str | None = typer.Option(None, "--since", help="Show logs since timestamp text"),
    level: str | None = typer.Option(None, "--level", help="Filter by level"),
) -> None:
    ctx = _ctx()
    log_file = ctx.paths.log_file
    if not log_file.exists():
        console.print(f"No logs found at {log_file}")
        raise typer.Exit(code=0)

    def _emit_lines() -> None:
        text = log_file.read_text(encoding="utf-8")
        for line in text.splitlines():
            if agent and agent not in line:
                continue
            if since and since not in line:
                continue
            if level and level.lower() not in line.lower():
                continue
            typer.echo(line)

    if not follow:
        _emit_lines()
        return

    last_size = 0
    while True:
        if log_file.exists():
            current = log_file.stat().st_size
            if current != last_size:
                _emit_lines()
                last_size = current
        time.sleep(1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
