"""Terminal chat — the same MCP + Claude loop without the UI.

Useful for learning and debugging: you see every tool call as it happens.

    python -m app.cli
"""

from __future__ import annotations

import json

from llm.agent import ClaudeAgent, ToolTrace
from mcp_client.runtime import MCPRuntime


def main() -> None:
    rt = MCPRuntime()
    mgr = rt.manager
    assert mgr
    for s in mgr.status.values():
        print(f"[{'ok' if s.connected else 'FAIL'}] {s.name}: {', '.join(s.tools) or s.error}")

    def show(t: ToolTrace) -> None:
        print(f"  -> {t.name}({json.dumps(t.arguments)})  [{'ok' if t.ok else 'error'}, {t.ms} ms]")

    agent = ClaudeAgent(tools=mgr.anthropic_tools(), call_tool=rt.call_tool)
    history: list[dict] = []
    print("\nType a request (or 'quit').")
    try:
        while (msg := input("\nyou> ").strip()).lower() not in {"quit", "exit"}:
            if not msg:
                continue
            history.append({"role": "user", "content": msg})
            reply = agent.chat(history, on_tool=show)
            print(f"\nassistant> {reply.text}\n  ({reply.usage['input_tokens']} in / {reply.usage['output_tokens']} out tokens)")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        rt.shutdown()


if __name__ == "__main__":
    main()
