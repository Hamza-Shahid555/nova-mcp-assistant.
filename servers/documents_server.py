"""Documents MCP Server — read and search files in data/documents/.

Supports .txt and .md out of the box; .pdf when `pypdf` is installed.
Run alone: python -m servers.documents_server
"""

from __future__ import annotations

import logging
import sys

from mcp.server.mcpserver import MCPServer

from app.config import DOCUMENTS_DIR
from database.doc_search import DocumentIndex

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="[documents] %(message)s")
log = logging.getLogger(__name__)

mcp = MCPServer(name="documents",
                instructions="Read-only access to the user's project documents. Search first, then read.")
index = DocumentIndex(DOCUMENTS_DIR)


@mcp.tool()
def list_documents() -> dict:
    """List available documents with their type and size."""
    docs = index.list()
    return {"ok": True, "count": len(docs), "documents": docs}


@mcp.tool()
def search_documents(query: str, top_k: int = 5) -> dict:
    """Find the most relevant passages across all documents (keyword TF-IDF ranking).

    Args:
        query: What to look for, e.g. "system architecture".
        top_k: Number of passages to return (1-10).
    """
    hits = index.search(query, top_k=max(1, min(top_k, 10)))
    return {"ok": True, "count": len(hits), "results": hits}


@mcp.tool()
def read_document(name: str, max_chars: int = 12000) -> dict:
    """Read a document's text by name (as returned by list_documents)."""
    try:
        return {"ok": True, "name": name, "text": index.read(name, max_chars=max(500, min(max_chars, 40000)))}
    except ValueError as e:
        return {"ok": False, "error": str(e)}


@mcp.resource("docs://index", name="document-index", mime_type="application/json",
              description="List of available documents")
def doc_index() -> list[dict]:
    return index.list()


@mcp.prompt(title="Explain architecture")
def explain_architecture(document: str = "") -> str:
    """Explain a project's architecture from its documents."""
    target = f"the document '{document}'" if document else "my project documents"
    return (f"Search {target} for architecture, components and data flow. Explain the architecture "
            "in plain language with a short component list and a step-by-step request flow. Cite file names.")


if __name__ == "__main__":
    log.info("starting documents server (dir=%s)", DOCUMENTS_DIR)
    mcp.run()
