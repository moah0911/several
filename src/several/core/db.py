from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    layout TEXT NOT NULL,
    agents_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    created_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS task_results (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    status TEXT NOT NULL,
    exit_code INTEGER,
    duration_ms INTEGER NOT NULL,
    output TEXT NOT NULL,
    workspace TEXT,
    tokens_used INTEGER,
    progress_percent INTEGER,
    tool_calls_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    agent TEXT,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);
"""


@dataclass
class TaskResultRecord:
    agent: str
    status: str
    exit_code: int | None
    duration_ms: int
    output: str
    workspace: str | None = None
    tokens_used: int | None = None
    progress_percent: int | None = None
    tool_calls: list[str] | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class StateStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            self._ensure_task_result_columns(conn)

    def _ensure_task_result_columns(self, conn: sqlite3.Connection) -> None:
        required = {
            "workspace": "TEXT",
            "tokens_used": "INTEGER",
            "progress_percent": "INTEGER",
            "tool_calls_json": "TEXT",
        }
        existing_rows = conn.execute("PRAGMA table_info(task_results)").fetchall()
        existing = {row["name"] for row in existing_rows}
        for column, ctype in required.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE task_results ADD COLUMN {column} {ctype}")

    def create_session(
        self, agents: list[str], layout: str = "grid", status: str = "active"
    ) -> str:
        session_id = f"sess-{uuid.uuid4().hex[:8]}"
        with self._connect() as conn:
            conn.execute(
                (
                    "INSERT INTO sessions "
                    "(id, created_at, status, layout, agents_json) "
                    "VALUES (?, ?, ?, ?, ?)"
                ),
                (session_id, now_iso(), status, layout, json.dumps(agents)),
            )
        return session_id

    def list_sessions(self, active_only: bool = False) -> list[dict[str, Any]]:
        query = "SELECT id, created_at, status, layout, agents_json FROM sessions"
        params: tuple[Any, ...] = ()
        if active_only:
            query += " WHERE status = ?"
            params = ("active",)
        query += " ORDER BY created_at DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "status": row["status"],
                    "layout": row["layout"],
                    "agents": json.loads(row["agents_json"]),
                    "task_count": self.task_count(row["id"]),
                }
            )
        return out

    def task_count(self, session_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM tasks WHERE session_id = ?", (session_id,)
            ).fetchone()
        return int(row["c"]) if row else 0

    def create_task(self, session_id: str, prompt: str, mode: str) -> str:
        task_id = f"task-{uuid.uuid4().hex[:10]}"
        with self._connect() as conn:
            conn.execute(
                (
                    "INSERT INTO tasks "
                    "(id, session_id, prompt, created_at, mode) "
                    "VALUES (?, ?, ?, ?, ?)"
                ),
                (task_id, session_id, prompt, now_iso(), mode),
            )
        return task_id

    def add_task_event(
        self, task_id: str, event_type: str, payload: dict[str, Any], agent: str | None = None
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO task_events (task_id, agent, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (task_id, agent, event_type, json.dumps(payload), now_iso()),
            )

    def list_task_events(
        self,
        session_id: str,
        task_id: str | None = None,
        agent: str | None = None,
        since_id: int | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        query = (
            "SELECT e.id, e.task_id, e.agent, e.event_type, e.payload_json, e.created_at "
            "FROM task_events e JOIN tasks t ON t.id = e.task_id WHERE t.session_id = ?"
        )
        params: list[Any] = [session_id]
        if task_id:
            query += " AND e.task_id = ?"
            params.append(task_id)
        if agent:
            query += " AND e.agent = ?"
            params.append(agent)
        if since_id is not None:
            query += " AND e.id > ?"
            params.append(since_id)
        query += " ORDER BY e.id ASC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "id": row["id"],
                    "task_id": row["task_id"],
                    "agent": row["agent"],
                    "event_type": row["event_type"],
                    "payload": json.loads(row["payload_json"] or "{}"),
                    "created_at": row["created_at"],
                }
            )
        return out

    def add_task_result(self, task_id: str, result: TaskResultRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO task_results
                (id, task_id, agent, status, exit_code, duration_ms, output, workspace,
                 tokens_used, progress_percent, tool_calls_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"res-{uuid.uuid4().hex[:10]}",
                    task_id,
                    result.agent,
                    result.status,
                    result.exit_code,
                    result.duration_ms,
                    result.output,
                    result.workspace,
                    result.tokens_used,
                    result.progress_percent,
                    json.dumps(result.tool_calls or []),
                    now_iso(),
                ),
            )

    def session_exists(self, session_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return row is not None

    def get_session(self, session_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, created_at, status, layout, agents_json FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Session not found: {session_id}")
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "status": row["status"],
            "layout": row["layout"],
            "agents": json.loads(row["agents_json"]),
            "task_count": self.task_count(session_id),
        }

    def delete_session(self, session_id: str) -> int:
        with self._connect() as conn:
            conn.execute(
                (
                    "DELETE FROM task_results "
                    "WHERE task_id IN (SELECT id FROM tasks WHERE session_id = ?)"
                ),
                (session_id,),
            )
            conn.execute("DELETE FROM tasks WHERE session_id = ?", (session_id,))
            cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            return cursor.rowcount

    def close_session(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE sessions SET status = 'closed' WHERE id = ?", (session_id,))

    def export_session(self, session_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            session = conn.execute(
                "SELECT id, created_at, status, layout, agents_json FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if session is None:
                raise KeyError(f"Session not found: {session_id}")

            tasks = conn.execute(
                (
                    "SELECT id, prompt, created_at, mode FROM tasks "
                    "WHERE session_id = ? ORDER BY created_at ASC"
                ),
                (session_id,),
            ).fetchall()

            result_rows = conn.execute(
                "SELECT task_id, agent, status, exit_code, duration_ms, output, workspace, "
                "tokens_used, progress_percent, tool_calls_json, created_at FROM task_results "
                "WHERE task_id IN (SELECT id FROM tasks WHERE session_id = ?)",
                (session_id,),
            ).fetchall()

        results_by_task: dict[str, list[dict[str, Any]]] = {}
        for row in result_rows:
            payload = dict(row)
            payload["tool_calls"] = json.loads(payload.pop("tool_calls_json") or "[]")
            results_by_task.setdefault(row["task_id"], []).append(payload)

        task_payload = []
        for task in tasks:
            task_payload.append(
                {
                    "id": task["id"],
                    "prompt": task["prompt"],
                    "created_at": task["created_at"],
                    "mode": task["mode"],
                    "results": results_by_task.get(task["id"], []),
                }
            )

        return {
            "session": {
                "id": session["id"],
                "created_at": session["created_at"],
                "status": session["status"],
                "layout": session["layout"],
                "agents": json.loads(session["agents_json"]),
            },
            "tasks": task_payload,
        }

    def import_session(self, payload: dict[str, Any]) -> str:
        session = payload.get("session", {})
        tasks = payload.get("tasks", [])
        session_id = session.get("id") or f"sess-{uuid.uuid4().hex[:8]}"

        with self._connect() as conn:
            conn.execute(
                (
                    "INSERT OR REPLACE INTO sessions "
                    "(id, created_at, status, layout, agents_json) "
                    "VALUES (?, ?, ?, ?, ?)"
                ),
                (
                    session_id,
                    session.get("created_at", now_iso()),
                    session.get("status", "closed"),
                    session.get("layout", "grid"),
                    json.dumps(session.get("agents", [])),
                ),
            )

            for task in tasks:
                task_id = task.get("id") or f"task-{uuid.uuid4().hex[:10]}"
                conn.execute(
                    (
                        "INSERT OR REPLACE INTO tasks "
                        "(id, session_id, prompt, created_at, mode) "
                        "VALUES (?, ?, ?, ?, ?)"
                    ),
                    (
                        task_id,
                        session_id,
                        task.get("prompt", ""),
                        task.get("created_at", now_iso()),
                        task.get("mode", "parallel"),
                    ),
                )

                for result in task.get("results", []):
                    conn.execute(
                        """
                        INSERT INTO task_results
                        (id, task_id, agent, status, exit_code, duration_ms, output, workspace,
                         tokens_used, progress_percent, tool_calls_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"res-{uuid.uuid4().hex[:10]}",
                            task_id,
                            result.get("agent", "unknown"),
                            result.get("status", "completed"),
                            result.get("exit_code"),
                            int(result.get("duration_ms", 0)),
                            result.get("output", ""),
                            result.get("workspace"),
                            result.get("tokens_used"),
                            result.get("progress_percent"),
                            json.dumps(result.get("tool_calls", [])),
                            result.get("created_at", now_iso()),
                        ),
                    )

        return session_id
