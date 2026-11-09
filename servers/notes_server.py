"""Notes MCP Server — Markdown notes stored as files in data/notes/.

Run alone: python -m servers.notes_server
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from mcp.server.mcpserver import MCPServer
from pydantic import ValidationError

from app.config import DB_PATH, NOTES_DIR
from database.db import TaskRepository
from database.models import NoteCreate
from database.notes_store import NotesStore

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="[notes] %(message)s")
log = logging.getLogger(__name__)

mcp = MCPServer(name="notes", instructions="Create, search, read and update the user's personal notes.")
store = NotesStore(NOTES_DIR)
activity = TaskRepository(DB_PATH)  # shared activity feed


def _preview(n: dict, chars: int = 200) -> dict:
    return {k: v for k, v in n.items() if k != "content"} | {"preview": n["content"][:chars]}


@mcp.tool()
def create_note(title: str, content: str, tags: Optional[list[str]] = None, important: bool = False) -> dict:
    """Create a note.

    Args:
        title: Note title.
        content: Markdown body.
        tags: Optional list of tags, e.g. ["rag", "ideas"].
        important: Flag the note as important.
    """
    try:
        note = store.create(NoteCreate(title=title, content=content, tags=tags or [], important=important))
        activity.log("notes", f"Created note “{title}”")
        return {"ok": True, "note": note}
    except ValidationError as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def search_notes(query: str = "", important_only: bool = False, tag: Optional[str] = None, limit: int = 10) -> dict:
    """Search notes by keywords in title, tags and body. Returns previews; use get_note for full text.

    Args:
        query: Keywords, e.g. "RAG chunking". Empty string lists all notes.
        important_only: Only notes flagged important.
        tag: Only notes with this tag.
    """
    hits = store.search(query, important_only=important_only, tag=tag)[: max(1, min(limit, 50))]
    return {"ok": True, "count": len(hits), "notes": [_preview(n) for n in hits]}


@mcp.tool()
def get_note(note_id: str) -> dict:
    """Return the full content of one note by its id (from search_notes)."""
    try:
        note = store.get(note_id)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "note": note} if note else {"ok": False, "error": f"Note '{note_id}' not found"}


@mcp.tool()
def update_note(note_id: str, title: Optional[str] = None, content: Optional[str] = None,
                tags: Optional[list[str]] = None, important: Optional[bool] = None, append: bool = False) -> dict:
    """Update a note. Set append=true to add content to the end instead of replacing it."""
    try:
        note = store.update(note_id, title=title, content=content, tags=tags, important=important, append=append)
        activity.log("notes", f"Updated note “{note['title']}”")
        return {"ok": True, "note": note}
    except ValueError as e:
        return {"ok": False, "error": str(e)}


@mcp.resource("notes://all", name="all-notes", mime_type="application/json", description="Index of all notes")
def all_notes() -> list[dict]:
    return [_preview(n, 120) for n in store.list()]


@mcp.resource("notes://{note_id}", name="note", mime_type="text/markdown", description="A single note's Markdown")
def note_resource(note_id: str) -> str:
    note = store.get(note_id)
    if not note:
        raise ValueError(f"Note '{note_id}' not found")
    return f"# {note['title']}\n\n{note['content']}"


@mcp.prompt(title="Study plan from notes")
def study_plan(topic: str) -> str:
    """Turn notes on a topic into a short study plan."""
    return (f"Search my notes about '{topic}', summarise what I already know, list the gaps, "
            "and suggest 3 concrete tasks (offer to create them).")


if __name__ == "__main__":
    log.info("starting notes server (dir=%s)", NOTES_DIR)
    mcp.run()
