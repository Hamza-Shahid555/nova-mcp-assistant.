"""Tasks MCP Server.

Exposes task management to any MCP client (our Streamlit app, Claude
Desktop, Cursor, ...). It speaks MCP over stdio: the client launches this
file as a subprocess and they exchange JSON-RPC messages over stdin/stdout.

    Tools     -> actions the LLM can take   (create_task, list_tasks, ...)
    Resources -> read-only data by URI      (tasks://stats, tasks://open)
    Prompts   -> reusable workflow templates (weekly_summary, plan_my_day)

Run alone for debugging:   python -m servers.tasks_server
Inspect interactively:     mcp dev servers/tasks_server.py   (needs `mcp[cli]`)

IMPORTANT: never print() in an stdio server — stdout carries the protocol.
Log to stderr instead.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import date
from typing import Literal, Optional

from mcp.server.mcpserver import MCPServer
from pydantic import ValidationError

from app.config import DB_PATH
from database.db import TaskRepository
from database.models import TaskCreate, TaskUpdate

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="[tasks] %(message)s")
log = logging.getLogger(__name__)

mcp = MCPServer(
    name="tasks",
    instructions="Manage the user's to-do tasks. Dates are ISO format YYYY-MM-DD. "
                 f"Today is resolved server-side; call get_today if you need it.",
)
repo = TaskRepository(DB_PATH)


def _err(e: Exception) -> dict:
    """Turn validation errors into a short message the LLM can act on."""
    if isinstance(e, ValidationError):
        msg = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())
    else:
        msg = str(e)
    log.warning("tool error: %s", msg)
    return {"ok": False, "error": msg}


# ------------------------------------------------------------------ tools
@mcp.tool()
def get_today() -> dict:
    """Return today's date and weekday. Use it to resolve words like 'tomorrow' or 'next Monday'."""
    d = date.today()
    return {"date": d.isoformat(), "weekday": d.strftime("%A")}


@mcp.tool()
def create_task(title: str, description: str = "", priority: Literal["low", "medium", "high"] = "medium",
                due_date: Optional[str] = None, project: str = "General") -> dict:
    """Create a new task.

    Args:
        title: Short task title, e.g. "Learn LangGraph".
        description: Optional details.
        priority: low | medium | high.
        due_date: ISO date YYYY-MM-DD (resolve relative dates with get_today first).
        project: Project name used to group tasks on the dashboard.
    """
    try:
        task = repo.create(TaskCreate(title=title, description=description, priority=priority,
                                      due_date=due_date, project=project))
        return {"ok": True, "task": task.model_dump(mode="json")}
    except Exception as e:  # noqa: BLE001 — always answer the client
        return _err(e)


@mcp.tool()
def list_tasks(status: Optional[Literal["todo", "in_progress", "done", "open"]] = None,
               project: Optional[str] = None, due_before: Optional[str] = None) -> dict:
    """List tasks with optional filters.

    Args:
        status: todo | in_progress | done | open (open = todo + in_progress). Omit for all.
        project: Only tasks in this project.
        due_before: ISO date; only tasks due on or before it (great for 'this week').
    """
    try:
        db_status = None if status == "open" else status
        tasks = repo.list(status=db_status, project=project,
                          due_before=date.fromisoformat(due_before) if due_before else None)
        if status == "open":
            tasks = [t for t in tasks if t.status != "done"]
        return {"ok": True, "count": len(tasks), "tasks": [t.model_dump(mode="json") for t in tasks]}
    except Exception as e:  # noqa: BLE001
        return _err(e)


@mcp.tool()
def update_task(task_id: int, title: Optional[str] = None, description: Optional[str] = None,
                priority: Optional[Literal["low", "medium", "high"]] = None,
                status: Optional[Literal["todo", "in_progress", "done"]] = None,
                due_date: Optional[str] = None, project: Optional[str] = None) -> dict:
    """Update any field of an existing task. Only pass the fields you want to change."""
    try:
        data = TaskUpdate(title=title, description=description, priority=priority,
                          status=status, due_date=due_date, project=project)
        return {"ok": True, "task": repo.update(task_id, data).model_dump(mode="json")}
    except Exception as e:  # noqa: BLE001
        return _err(e)


@mcp.tool()
def complete_task(task_id: int) -> dict:
    """Mark a task as completed."""
    try:
        return {"ok": True, "task": repo.complete(task_id).model_dump(mode="json")}
    except Exception as e:  # noqa: BLE001
        return _err(e)


@mcp.tool()
def delete_task(task_id: int) -> dict:
    """Permanently delete a task. Confirm with the user first if the request is ambiguous."""
    deleted = repo.delete(task_id)
    return {"ok": deleted, **({} if deleted else {"error": f"Task {task_id} not found"})}


@mcp.tool()
def task_stats() -> dict:
    """Counts for the dashboard: due today, in progress, completed, overdue, per-project progress."""
    return {"ok": True, **repo.stats()}


@mcp.tool()
def recent_activity(limit: int = 10) -> dict:
    """Recent actions taken on tasks and notes (the dashboard activity feed)."""
    return {"ok": True, "activity": repo.recent_activity(max(1, min(limit, 50)))}


# -------------------------------------------------------------- resources
@mcp.resource("tasks://stats", name="task-stats", mime_type="application/json",
              description="Live task statistics")
def stats_resource() -> str:
    return json.dumps(repo.stats())


@mcp.resource("tasks://open", name="open-tasks", mime_type="application/json",
              description="All tasks that are not done")
def open_tasks_resource() -> str:
    return json.dumps([t.model_dump(mode="json") for t in repo.list() if t.status != "done"])


# ---------------------------------------------------------------- prompts
@mcp.prompt(title="Weekly summary")
def weekly_summary() -> str:
    """Summarise this week's tasks."""
    return ("Use list_tasks and task_stats to summarise my week: what is done, what is in progress, "
            "what is overdue, and the top 3 things I should focus on next. Keep it short and use bullets.")


@mcp.prompt(title="Plan my day")
def plan_my_day(hours_available: int = 6) -> str:
    """Build a realistic plan for today."""
    return (f"I have about {hours_available} hours today. Look at my open tasks (high priority and "
            "overdue first) and propose a time-blocked plan. Ask before changing anything.")


if __name__ == "__main__":
    log.info("starting tasks server (db=%s)", DB_PATH)
    mcp.run()  # stdio transport by default
