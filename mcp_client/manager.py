"""MCP Client manager — one host, many servers.

How it works
------------
1. For each server in SERVERS we spawn a subprocess (stdio transport) and
   open a ClientSession over its stdin/stdout.
2. `initialize()` performs the MCP handshake (protocol version + capabilities).
3. `list_tools()` asks every server what it can do (tool discovery). We store
   each tool under a qualified name "server__tool" so two servers can both
   have e.g. a `search` tool without clashing.
4. `call_tool("tasks__create_task", {...})` routes the call to the right
   session and returns the result.

The LLM never talks to servers directly — it only sees tool *schemas* and
asks us to call them. That separation is the heart of MCP.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import PROJECT_ROOT

log = logging.getLogger(__name__)
SEP = "__"


@dataclass
class ServerConfig:
    name: str
    module: str  # python module to run with `python -m`
    description: str = ""


SERVERS = [
    ServerConfig("tasks", "servers.tasks_server", "Task management (SQLite)"),
    ServerConfig("notes", "servers.notes_server", "Markdown notes"),
    ServerConfig("documents", "servers.documents_server", "Document search"),
]

# The stdio transport only forwards a few safe env vars to the subprocess,
# so we pass our own settings explicitly.
FORWARD_ENV = ("DATA_DIR", "DB_PATH", "NOTES_DIR", "DOCUMENTS_DIR", "PYTHONPATH")


@dataclass
class ToolInfo:
    server: str
    name: str
    description: str
    input_schema: dict

    @property
    def qualified(self) -> str:
        return f"{self.server}{SEP}{self.name}"


@dataclass
class ServerStatus:
    name: str
    connected: bool = False
    error: str = ""
    tools: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    server_version: str = ""


class MCPClientManager:
    """Async context manager that owns every server connection."""

    def __init__(self, servers: list[ServerConfig] | None = None):
        self.servers = servers or SERVERS
        self.sessions: dict[str, ClientSession] = {}
        self.tools: dict[str, ToolInfo] = {}
        self.status: dict[str, ServerStatus] = {}
        self._stack = AsyncExitStack()

    async def __aenter__(self) -> "MCPClientManager":
        await self.connect_all()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    # ---------------------------------------------------------- lifecycle
    def _params(self, cfg: ServerConfig) -> StdioServerParameters:
        env = {k: os.environ[k] for k in FORWARD_ENV if k in os.environ}
        env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONIOENCODING"] = "utf-8"
        return StdioServerParameters(command=sys.executable, args=["-m", cfg.module],
                                     cwd=str(PROJECT_ROOT), env=env)

    async def connect_all(self) -> None:
        for cfg in self.servers:
            st = ServerStatus(cfg.name)
            self.status[cfg.name] = st
            try:
                read, write = await self._stack.enter_async_context(stdio_client(self._params(cfg)))
                session = await self._stack.enter_async_context(ClientSession(read, write))
                init = await session.initialize()
                st.server_version = getattr(init.server_info, "version", "") or ""
                self.sessions[cfg.name] = session
                await self._discover(cfg.name, session, st)
                st.connected = True
                log.info("connected to %s (%d tools)", cfg.name, len(st.tools))
            except Exception as e:  # noqa: BLE001 — one bad server must not kill the app
                st.error = f"{type(e).__name__}: {e}"
                log.exception("failed to connect to %s", cfg.name)

    async def _discover(self, name: str, session: ClientSession, st: ServerStatus) -> None:
        tools = await session.list_tools()
        for t in tools.tools:
            info = ToolInfo(name, t.name, t.description or "", t.input_schema or {"type": "object"})
            self.tools[info.qualified] = info
            st.tools.append(t.name)
        for attr, lister, key in (("resources", "list_resources", "uri"), ("prompts", "list_prompts", "name")):
            try:
                res = await getattr(session, lister)()
                setattr(st, attr, [str(getattr(x, key)) for x in getattr(res, attr)])
            except Exception:  # server may not support it
                pass

    async def close(self) -> None:
        await self._stack.aclose()
        self.sessions.clear()

    # ---------------------------------------------------------- tool calls
    def anthropic_tools(self) -> list[dict]:
        """Convert MCP tool schemas into the format Claude's API expects."""
        return [{"name": t.qualified, "description": f"[{t.server}] {t.description}".strip(),
                 "input_schema": t.input_schema} for t in self.tools.values()]

    async def call_tool(self, qualified: str, arguments: dict[str, Any] | None = None) -> dict:
        """Route a call to the right server. Always returns a dict, never raises."""
        start = time.perf_counter()
        info = self.tools.get(qualified)
        if not info:
            return {"ok": False, "is_error": True, "text": f"Unknown tool '{qualified}'", "ms": 0}
        session = self.sessions.get(info.server)
        if not session:
            return {"ok": False, "is_error": True, "text": f"Server '{info.server}' is not connected", "ms": 0}
        try:
            result = await session.call_tool(info.name, arguments or {}, read_timeout_seconds=60)
            parts = [c.text for c in result.content if getattr(c, "type", "") == "text"]
            text = "\n".join(parts) if parts else json.dumps(result.structured_content or {})
            data = None
            try:
                data = json.loads(text)
            except (ValueError, TypeError):
                pass
            is_error = bool(result.is_error) or (isinstance(data, dict) and data.get("ok") is False)
            return {"ok": not is_error, "is_error": is_error, "text": text, "data": data,
                    "server": info.server, "tool": info.name,
                    "ms": round((time.perf_counter() - start) * 1000)}
        except Exception as e:  # noqa: BLE001 — transport/timeouts
            log.exception("tool call failed: %s", qualified)
            return {"ok": False, "is_error": True, "text": f"{type(e).__name__}: {e}",
                    "server": info.server, "tool": info.name,
                    "ms": round((time.perf_counter() - start) * 1000)}

    async def read_resource(self, server: str, uri: str) -> str:
        res = await self.sessions[server].read_resource(uri)
        return "\n".join(getattr(c, "text", "") for c in res.contents)

    async def get_prompt(self, server: str, name: str, arguments: dict[str, str] | None = None) -> str:
        res = await self.sessions[server].get_prompt(name, arguments or {})
        return "\n".join(getattr(m.content, "text", "") for m in res.messages)


def project_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)
