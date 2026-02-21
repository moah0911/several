from __future__ import annotations

import asyncio
from typing import Any, Callable

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Footer, Header, Input, ProgressBar, Static


class SeveralApp(App[None]):
    CSS = """
    Screen {
      layout: vertical;
    }
    #content {
      height: 1fr;
    }
    .panel {
      border: solid $accent;
      padding: 1;
      margin: 1;
    }
    Input {
      dock: bottom;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(
        self,
        active_agents: list[str],
        layout: str = "grid",
        task_submitter: Callable[[str, Callable[[dict[str, Any]], None] | None], str] | None = None,
    ) -> None:
        super().__init__()
        self.active_agents = active_agents
        self.layout = layout
        self.task_submitter = task_submitter
        self.agent_widgets: dict[str, Static] = {}
        self.agent_progress: dict[str, ProgressBar] = {}
        self.output_lines: list[str] = []

    class TaskDone(Message):
        def __init__(self, output: str) -> None:
            self.output = output
            super().__init__()

    class TaskEvent(Message):
        def __init__(self, event: dict[str, Any]) -> None:
            self.event = event
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        if self.layout == "vertical":
            with Vertical(id="content"):
                for agent in self.active_agents:
                    with Vertical(classes="panel", id=f"agent-panel-{agent}"):
                        status = Static(f"{agent}: ready", id=f"agent-status-{agent}")
                        progress = ProgressBar(total=100, id=f"agent-progress-{agent}")
                        self.agent_widgets[agent] = status
                        self.agent_progress[agent] = progress
                        yield status
                        yield progress
        else:
            with Horizontal(id="content"):
                for agent in self.active_agents:
                    with Vertical(classes="panel", id=f"agent-panel-{agent}"):
                        status = Static(f"{agent}: ready", id=f"agent-status-{agent}")
                        progress = ProgressBar(total=100, id=f"agent-progress-{agent}")
                        self.agent_widgets[agent] = status
                        self.agent_progress[agent] = progress
                        yield status
                        yield progress
        yield Static("Ready", classes="panel", id="task-output")
        yield Input(placeholder="Type a task and press Enter")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return

        event.input.value = ""
        for agent, widget in self.agent_widgets.items():
            widget.update(f"{agent}: running...")
            progress = self.agent_progress.get(agent)
            if progress is not None:
                progress.update(progress=0, total=100)

        output_widget = self.query_one("#task-output", Static)
        output_widget.update("Running task...")
        self.output_lines = []

        if self.task_submitter is None:
            output_widget.update("No task submitter configured.")
            return

        def report(evt: dict[str, Any]) -> None:
            self.call_from_thread(self.post_message, self.TaskEvent(evt))

        rendered = await asyncio.to_thread(self.task_submitter, prompt, report)
        self.post_message(self.TaskDone(rendered))

    def on_several_app_task_done(self, message: TaskDone) -> None:
        output_widget = self.query_one("#task-output", Static)
        output_widget.update(message.output[:4000])
        self.output_lines = message.output.splitlines()[-200:]
        for agent, widget in self.agent_widgets.items():
            widget.update(f"{agent}: ready")

    def on_several_app_task_event(self, message: TaskEvent) -> None:
        event = message.event
        agent = str(event.get("agent", ""))
        if not agent:
            return

        status_widget = self.agent_widgets.get(agent)
        progress_widget = self.agent_progress.get(agent)

        if event.get("type") == "workspace" and status_widget is not None:
            status_widget.update(f"{agent}: workspace ready")
        elif event.get("type") == "start" and status_widget is not None:
            status_widget.update(f"{agent}: running...")
        elif event.get("type") == "result" and status_widget is not None:
            status_widget.update(f"{agent}: {event.get('status', 'completed')}")
        elif event.get("type") == "output":
            line = str(event.get("line", ""))
            if line:
                self.output_lines.append(f"[{agent}] {line}")
                self.output_lines = self.output_lines[-200:]
                self.query_one("#task-output", Static).update("\n".join(self.output_lines[-40:]))

        if progress_widget is not None and isinstance(event.get("progress"), int):
            progress_widget.update(progress=int(event["progress"]), total=100)
