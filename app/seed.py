"""Load demo data so the dashboard is not empty on first run.

python -m app.seed          # add demo data (skips if tasks already exist)
python -m app.seed --reset  # wipe tasks/activity and re-seed
"""

from __future__ import annotations

import sys
from datetime import date, timedelta

from app.config import DB_PATH, DOCUMENTS_DIR, NOTES_DIR
from database.db import TaskRepository
from database.models import NoteCreate, TaskCreate, TaskUpdate
from database.notes_store import NotesStore

T = date.today()
D = lambda n: T + timedelta(days=n)  # noqa: E731

TASKS = [
    ("Finish MCP client connection manager", "MCP Assistant", "high", D(0), "in_progress"),
    ("Write README architecture section", "MCP Assistant", "medium", D(1), "todo"),
    ("Record 2-minute demo video", "MCP Assistant", "medium", D(4), "todo"),
    ("Set up project structure", "MCP Assistant", "low", D(-3), "done"),
    ("Build tasks MCP server", "MCP Assistant", "high", D(-1), "done"),
    ("Learn LangGraph basics", "Learning", "medium", D(1), "todo"),
    ("Revise RAG chunking strategies", "Learning", "high", D(0), "todo"),
    ("Finish CampusX MCP course notes", "Learning", "low", D(-2), "done"),
    ("Update LinkedIn with MCP project", "Career", "medium", D(-1), "todo"),
    ("Apply to 3 AI engineer roles", "Career", "high", D(2), "in_progress"),
]

NOTES = [
    ("RAG chunking ideas", "Try 500–800 token chunks with 10% overlap.\nUse heading-aware splitting for reports.\n"
     "Evaluate retrieval with a small labelled question set before tuning.", ["rag", "retrieval"], True),
    ("MCP key concepts", "- Host: the app the user talks to\n- Client: one connection per server\n"
     "- Server: exposes tools, resources, prompts\n- Transport: stdio for local, streamable HTTP for remote",
     ["mcp"], True),
    ("LangGraph reading list", "Start with the official quickstart, then state graphs and checkpointers.",
     ["langgraph", "learning"], False),
    ("Demo video script draft", "1. Problem\n2. Architecture diagram\n3. Live: create task by chat\n"
     "4. Search notes + documents\n5. What I learned", ["career"], False),
]

DOC = """# MCP Productivity Assistant — Architecture

## Overview
The assistant is an MCP Host built with Streamlit. It connects to three MCP servers over the stdio
transport: a Tasks server backed by SQLite, a Notes server backed by Markdown files, and a
Documents server that searches TXT, Markdown and PDF files.

## Components
- Streamlit UI: dashboard, chat, task board, notes and documents pages.
- LLM layer: Claude receives the user message plus every discovered MCP tool schema and decides
  which tool to call.
- MCP Client manager: spawns each server as a subprocess, performs the initialize handshake,
  discovers tools with tools/list and routes tools/call requests to the right session.
- MCP Servers: each exposes Tools (actions), Resources (read-only data by URI) and Prompts
  (reusable workflows).

## Request flow
1. The user types "Create a task to learn LangGraph tomorrow".
2. The app sends the conversation and tool schemas to Claude.
3. Claude replies with a tool_use block for tasks__create_task.
4. The MCP client calls create_task on the Tasks server, which validates input with Pydantic and
   writes to SQLite.
5. The result returns to Claude as a tool_result and Claude writes the final answer.

## Error handling
Servers never crash on bad input: they return ok=false with a readable error so the LLM can
recover. A server that fails to start is marked disconnected and the others keep working.
"""


def main(reset: bool = False) -> None:
    repo = TaskRepository(DB_PATH)
    if reset:
        import sqlite3
        with sqlite3.connect(DB_PATH) as c:
            c.executescript("DELETE FROM tasks; DELETE FROM activity;")
    if repo.list() and not reset:
        print("Tasks already exist — skipping (use --reset to wipe).")
        return
    for title, project, prio, due, status in TASKS:
        t = repo.create(TaskCreate(title=title, project=project, priority=prio, due_date=due))
        if status != "todo":
            repo.update(t.id, TaskUpdate(status=status))
    notes = NotesStore(NOTES_DIR)
    if not notes.list():
        for title, content, tags, imp in NOTES:
            notes.create(NoteCreate(title=title, content=content, tags=tags, important=imp))
            repo.log("notes", f"Created note “{title}”")
    arch = DOCUMENTS_DIR / "project_architecture.md"
    if not arch.exists():
        arch.write_text(DOC, encoding="utf-8")
    print(f"Seeded {len(TASKS)} tasks, {len(NOTES)} notes, 1 document.")


if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
