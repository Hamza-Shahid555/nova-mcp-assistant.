"""SQLite persistence for tasks and the activity feed.

This module knows nothing about MCP. Keeping storage separate from the
protocol layer means you can unit-test it alone and swap SQLite for
Postgres later without touching the MCP servers.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional

from database.models import Task, TaskCreate, TaskUpdate

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    priority     TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high')),
    status       TEXT NOT NULL DEFAULT 'todo'   CHECK (status IN ('todo','in_progress','done')),
    due_date     TEXT,
    project      TEXT NOT NULL DEFAULT 'General',
    created_at   TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS activity (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source     TEXT NOT NULL,
    message    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class TaskRepository:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _row(r: sqlite3.Row) -> Task:
        return Task(**dict(r))

    # ---------- activity ----------
    def log(self, source: str, message: str) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO activity(source,message,created_at) VALUES (?,?,?)",
                      (source, message, _now()))

    def recent_activity(self, limit: int = 10) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    # ---------- tasks ----------
    def create(self, data: TaskCreate) -> Task:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO tasks(title,description,priority,due_date,project,created_at) VALUES (?,?,?,?,?,?)",
                (data.title, data.description, data.priority,
                 data.due_date.isoformat() if data.due_date else None, data.project, _now()),
            )
            task_id = cur.lastrowid
        self.log("tasks", f"Created task “{data.title}”")
        return self.get(task_id)  # type: ignore[return-value]

    def get(self, task_id: int) -> Optional[Task]:
        with self._conn() as c:
            r = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return self._row(r) if r else None

    def list(self, status: Optional[str] = None, project: Optional[str] = None,
             due_before: Optional[date] = None) -> list[Task]:
        sql, args = "SELECT * FROM tasks WHERE 1=1", []
        if status:
            sql += " AND status=?"; args.append(status)
        if project:
            sql += " AND lower(project)=lower(?)"; args.append(project)
        if due_before:
            sql += " AND due_date IS NOT NULL AND due_date<=?"; args.append(due_before.isoformat())
        sql += (" ORDER BY CASE status WHEN 'done' THEN 1 ELSE 0 END,"
                " due_date IS NULL, due_date,"
                " CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id")
        with self._conn() as c:
            return [self._row(r) for r in c.execute(sql, args).fetchall()]

    def update(self, task_id: int, data: TaskUpdate) -> Task:
        existing = self.get(task_id)
        if not existing:
            raise ValueError(f"Task {task_id} not found")
        fields = data.model_dump(exclude_unset=True, exclude_none=True)
        if not fields:
            return existing
        if "due_date" in fields:
            fields["due_date"] = fields["due_date"].isoformat()
        if fields.get("status") == "done" and existing.status != "done":
            fields["completed_at"] = _now()
        elif "status" in fields and fields["status"] != "done":
            fields["completed_at"] = None
        cols = ", ".join(f"{k}=?" for k in fields)
        with self._conn() as c:
            c.execute(f"UPDATE tasks SET {cols} WHERE id=?", (*fields.values(), task_id))
        verb = "Completed" if fields.get("status") == "done" else "Updated"
        self.log("tasks", f"{verb} task “{existing.title}”")
        return self.get(task_id)  # type: ignore[return-value]

    def complete(self, task_id: int) -> Task:
        return self.update(task_id, TaskUpdate(status="done"))

    def delete(self, task_id: int) -> bool:
        existing = self.get(task_id)
        if not existing:
            return False
        with self._conn() as c:
            c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self.log("tasks", f"Deleted task “{existing.title}”")
        return True

    # ---------- dashboard ----------
    def stats(self) -> dict:
        today = date.today()
        tasks = self.list()
        open_tasks = [t for t in tasks if t.status != "done"]
        done_today = [t for t in tasks if t.completed_at and t.completed_at[:10] == today.isoformat()]
        week_end = today + timedelta(days=(6 - today.weekday()))
        projects: dict[str, dict] = {}
        for t in tasks:
            p = projects.setdefault(t.project, {"total": 0, "done": 0})
            p["total"] += 1
            p["done"] += t.status == "done"
        return {
            "total": len(tasks),
            "due_today": sum(1 for t in open_tasks if t.due_date == today),
            "in_progress": sum(1 for t in tasks if t.status == "in_progress"),
            "todo": sum(1 for t in tasks if t.status == "todo"),
            "completed": sum(1 for t in tasks if t.status == "done"),
            "completed_today": len(done_today),
            "overdue": sum(1 for t in open_tasks if t.due_date and t.due_date < today),
            "due_this_week": sum(1 for t in open_tasks if t.due_date and today <= t.due_date <= week_end),
            "projects": {k: {**v, "pct": round(100 * v["done"] / v["total"])} for k, v in projects.items()},
        }
