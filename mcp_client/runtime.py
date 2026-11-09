"""Bridge between synchronous Streamlit and the async MCP client.

Streamlit re-runs your script top-to-bottom on every click, but MCP
sessions are long-lived async objects. So we run ONE asyncio event loop in
a background thread, keep the MCPClientManager alive inside it, and submit
work to that loop with `run_coroutine_threadsafe`.

    Streamlit thread ──submit(coro)──▶ background loop ──▶ MCP sessions
                     ◀──── result ────

The manager is opened and closed inside a single "owner" task because the
MCP SDK (anyio) requires a context to be exited by the same task that
entered it.
"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Any, Coroutine, TypeVar

from mcp_client.manager import MCPClientManager

T = TypeVar("T")


class MCPRuntime:
    def __init__(self, connect_timeout: float = 60):
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self.loop.run_forever, name="mcp-loop", daemon=True)
        self._thread.start()
        self._ready: Future = Future()
        self._stop: asyncio.Event | None = None
        self.manager: MCPClientManager | None = None
        asyncio.run_coroutine_threadsafe(self._owner(), self.loop)
        self._ready.result(timeout=connect_timeout)

    async def _owner(self) -> None:
        self._stop = asyncio.Event()
        try:
            async with MCPClientManager() as manager:
                self.manager = manager
                self._ready.set_result(True)
                await self._stop.wait()
        except Exception as e:  # noqa: BLE001
            if not self._ready.done():
                self._ready.set_exception(e)

    def run(self, coro: Coroutine[Any, Any, T], timeout: float = 120) -> T:
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout=timeout)

    # convenience wrappers ------------------------------------------------
    def call_tool(self, name: str, args: dict | None = None) -> dict:
        assert self.manager
        return self.run(self.manager.call_tool(name, args or {}))

    def data(self, name: str, args: dict | None = None) -> dict:
        """Call a tool and return its parsed JSON (or {} on error)."""
        res = self.call_tool(name, args)
        return res.get("data") or {} if res["ok"] else {}

    def get_prompt(self, server: str, name: str, args: dict | None = None) -> str:
        assert self.manager
        return self.run(self.manager.get_prompt(server, name, args))

    def shutdown(self) -> None:
        if self._stop:
            self.loop.call_soon_threadsafe(self._stop.set)
