"""File-based notes: one Markdown file per note with a small header block.

    ---
    title: RAG chunking ideas
    tags: rag, retrieval
    important: true
    updated: 2026-11-09T14:00:00
    ---
    body text...

Plain files are easy to inspect, version with Git, and edit by hand.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from database.models import NoteCreate


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "note"


class NotesStore:
    def __init__(self, notes_dir: Path):
        self.dir = Path(notes_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    # ---------- file format ----------
    @staticmethod
    def _render(title: str, content: str, tags: list[str], important: bool) -> str:
        return (f"---\ntitle: {title}\ntags: {', '.join(tags)}\nimportant: {str(important).lower()}\n"
                f"updated: {datetime.now().isoformat(timespec='seconds')}\n---\n{content.strip()}\n")

    def _parse(self, path: Path) -> dict:
        raw = path.read_text(encoding="utf-8")
        meta, body = {}, raw
        m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.S)
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = m.group(2)
        return {
            "id": path.stem,
            "title": meta.get("title", path.stem),
            "tags": [t.strip() for t in meta.get("tags", "").split(",") if t.strip()],
            "important": meta.get("important", "false") == "true",
            "updated": meta.get("updated", ""),
            "content": body.strip(),
        }

    def _path(self, note_id: str) -> Path:
        # Guard against path traversal: ids are slugs only.
        if not re.fullmatch(r"[a-z0-9-]+", note_id):
            raise ValueError("Invalid note id")
        return self.dir / f"{note_id}.md"

    # ---------- CRUD ----------
    def create(self, data: NoteCreate) -> dict:
        base = slugify(data.title)
        note_id, n = base, 2
        while (self.dir / f"{note_id}.md").exists():
            note_id, n = f"{base}-{n}", n + 1
        self._path(note_id).write_text(
            self._render(data.title, data.content, data.tags, data.important), encoding="utf-8")
        return self.get(note_id)  # type: ignore[return-value]

    def get(self, note_id: str) -> Optional[dict]:
        p = self._path(note_id)
        return self._parse(p) if p.exists() else None

    def list(self) -> list[dict]:
        notes = [self._parse(p) for p in self.dir.glob("*.md")]
        return sorted(notes, key=lambda n: n["updated"], reverse=True)

    def update(self, note_id: str, title: Optional[str] = None, content: Optional[str] = None,
               tags: Optional[list[str]] = None, important: Optional[bool] = None,
               append: bool = False) -> dict:
        note = self.get(note_id)
        if not note:
            raise ValueError(f"Note '{note_id}' not found")
        new_content = note["content"]
        if content is not None:
            new_content = f"{note['content']}\n\n{content}" if append else content
        self._path(note_id).write_text(self._render(
            title or note["title"], new_content,
            tags if tags is not None else note["tags"],
            important if important is not None else note["important"]), encoding="utf-8")
        return self.get(note_id)  # type: ignore[return-value]

    def search(self, query: str, important_only: bool = False, tag: Optional[str] = None) -> list[dict]:
        terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 1]
        results = []
        for n in self.list():
            if important_only and not n["important"]:
                continue
            if tag and tag.lower() not in [t.lower() for t in n["tags"]]:
                continue
            hay_title = n["title"].lower()
            hay = f"{hay_title} {' '.join(n['tags']).lower()} {n['content'].lower()}"
            score = sum(hay.count(t) + 3 * hay_title.count(t) for t in terms) if terms else 1
            if score:
                results.append({**n, "score": score})
        return sorted(results, key=lambda n: n["score"], reverse=True)
