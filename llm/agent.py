"""The LLM layer: Claude decides, MCP executes.

The tool-calling loop
---------------------
    1. Send the conversation + the list of MCP tool schemas to Claude.
    2. If Claude replies with `tool_use` blocks, run each one through the
       MCP client and send the results back as `tool_result` blocks.
    3. Repeat until Claude replies with plain text (stop_reason != tool_use)
       or we hit MAX_TOOL_ROUNDS (a safety limit against infinite loops).

Note the split of responsibilities: Claude's *native tool calling* is how
the model asks for an action; *MCP* is how our app discovers and executes
that action on a server. They are two different layers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, Optional

from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ASSISTANT_NAME, MAX_TOOL_ROUNDS, USER_NAME


def system_prompt() -> str:
    today = date.today()
    return (
        f"You are {ASSISTANT_NAME}, a personal productivity assistant for {USER_NAME}. "
        f"Today is {today.strftime('%A')}, {today.isoformat()}.\n"
        "You can manage tasks, notes and project documents ONLY through the provided tools "
        "(they are MCP tools named server__tool). Rules:\n"
        "- Resolve relative dates ('tomorrow', 'this week') yourself using today's date; pass ISO dates.\n"
        "- Before updating/completing/deleting a task by name, call list_tasks to find its id.\n"
        "- When answering from documents or notes, search first and mention which file/note you used.\n"
        "- If a tool returns ok=false, explain the problem briefly and suggest a fix.\n"
        "- Keep answers short, friendly and scannable (bullets for lists)."
    )


@dataclass
class ToolTrace:
    name: str
    arguments: dict
    ok: bool
    output: str
    ms: int


@dataclass
class AgentReply:
    text: str
    traces: list[ToolTrace] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


class ClaudeAgent:
    def __init__(self, tools: list[dict], call_tool: Callable[[str, dict], dict],
                 api_key: str = ANTHROPIC_API_KEY, model: str = ANTHROPIC_MODEL):
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        import anthropic  # imported lazily so the app runs without it for UI-only work

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.tools = tools
        self.call_tool = call_tool

    def chat(self, history: list[dict], on_tool: Optional[Callable[[ToolTrace], None]] = None) -> AgentReply:
        """Run the loop. `history` is mutated in place (Anthropic message format)."""
        traces: list[ToolTrace] = []
        usage = {"input_tokens": 0, "output_tokens": 0}
        for _ in range(MAX_TOOL_ROUNDS):
            resp = self.client.messages.create(
                model=self.model, max_tokens=2048, system=system_prompt(),
                tools=self.tools, messages=history,
            )
            usage["input_tokens"] += resp.usage.input_tokens
            usage["output_tokens"] += resp.usage.output_tokens
            history.append({"role": "assistant",
                            "content": [b.model_dump(exclude_none=True) for b in resp.content]})

            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if resp.stop_reason != "tool_use" or not tool_uses:
                text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
                return AgentReply(text or "(no response)", traces, usage)

            results: list[dict[str, Any]] = []
            for tu in tool_uses:
                res = self.call_tool(tu.name, dict(tu.input))
                trace = ToolTrace(tu.name, dict(tu.input), res["ok"], res["text"], res.get("ms", 0))
                traces.append(trace)
                if on_tool:
                    on_tool(trace)
                results.append({"type": "tool_result", "tool_use_id": tu.id,
                                "content": res["text"][:20_000], "is_error": res["is_error"]})
            history.append({"role": "user", "content": results})

        return AgentReply("I stopped after too many tool steps. Try a more specific request.", traces, usage)


def pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)
