"""Keyword search over local documents (TXT, Markdown, optional PDF).

Deliberately simple — no embeddings yet. Documents are split into
paragraph chunks and scored with a small TF-IDF so the most relevant
passages come back first. This is the spot to plug RAG in later.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

SUPPORTED = {".txt", ".md", ".markdown", ".pdf"}
STOP = set("the a an and or of to in on for is are was were be with as by at it this that from".split())


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP and len(t) > 1]


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader  # optional dependency
        except ImportError:
            raise ValueError("PDF support needs `pip install pypdf`")
        return "\n\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    return path.read_text(encoding="utf-8", errors="ignore")


class DocumentIndex:
    def __init__(self, docs_dir: Path, chunk_chars: int = 900):
        self.dir = Path(docs_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.chunk_chars = chunk_chars

    def _safe(self, name: str) -> Path:
        p = (self.dir / name).resolve()
        if self.dir.resolve() not in p.parents or not p.exists():
            raise ValueError(f"Document '{name}' not found")
        if p.suffix.lower() not in SUPPORTED:
            raise ValueError(f"Unsupported file type: {p.suffix}")
        return p

    def list(self) -> list[dict]:
        out = []
        for p in sorted(self.dir.rglob("*")):
            if p.is_file() and p.suffix.lower() in SUPPORTED:
                out.append({"name": str(p.relative_to(self.dir)).replace("\\", "/"),
                            "type": p.suffix.lower().lstrip("."), "size_kb": round(p.stat().st_size / 1024, 1)})
        return out

    def read(self, name: str, max_chars: int = 20_000) -> str:
        text = read_text(self._safe(name))
        return text if len(text) <= max_chars else text[:max_chars] + "\n\n[...truncated]"

    def _chunks(self) -> list[dict]:
        chunks = []
        for d in self.list():
            try:
                text = read_text(self.dir / d["name"])
            except ValueError:
                continue
            buf = ""
            for para in re.split(r"\n\s*\n", text):
                if len(buf) + len(para) > self.chunk_chars and buf:
                    chunks.append({"document": d["name"], "text": buf.strip()})
                    buf = ""
                buf += para + "\n\n"
            if buf.strip():
                chunks.append({"document": d["name"], "text": buf.strip()})
        return chunks

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        q = _tokens(query)
        chunks = self._chunks()
        if not q or not chunks:
            return []
        tok = [Counter(_tokens(c["text"])) for c in chunks]
        n = len(chunks)
        idf = {t: math.log((n + 1) / (1 + sum(1 for c in tok if t in c))) + 1 for t in set(q)}
        scored = []
        for c, counts in zip(chunks, tok):
            score = sum((1 + math.log(counts[t])) * idf[t] for t in q if counts[t])
            if score > 0:
                scored.append({**c, "score": round(score, 3)})
        return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_k]
