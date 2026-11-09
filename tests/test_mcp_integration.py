"""Integration tests — real MCP servers over stdio, plus the Claude loop with a fake model.

These spawn the actual server subprocesses, so they test the protocol
end-to-end: handshake, tool discovery, tool calls, resources and prompts.
"""

import json
from types import SimpleNamespace as NS

import pytest

from mcp_client.runtime import MCPRuntime


@pytest.fixture(scope="module")
def rt(tmp_path_factory, monkeypatch_module):
    data = tmp_path_factory.mktemp("data")
    monkeypatch_module.setenv("DATA_DIR", str(data))
    monkeypatch_module.setenv("DB_PATH", str(data / "test.db"))
    monkeypatch_module.setenv("NOTES_DIR", str(data / "notes"))
    monkeypatch_module.setenv("DOCUMENTS_DIR", str(data / "docs"))
    (data / "docs").mkdir()
    (data / "docs" / "arch.md").write_text("The host connects to three MCP servers over stdio.")
    runtime = MCPRuntime()
    yield runtime
    runtime.shutdown()


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def test_all_servers_connect_and_discover_tools(rt):
    st = rt.manager.status
    assert all(s.connected for s in st.values()), {k: v.error for k, v in st.items()}
    names = set(rt.manager.tools)
    assert {"tasks__create_task", "notes__search_notes", "documents__search_documents"} <= names
    for tool in rt.manager.anthropic_tools():
        assert tool["input_schema"]["type"] == "object"


def test_task_roundtrip(rt):
    res = rt.call_tool("tasks__create_task", {"title": "Integration", "due_date": "2030-01-01"})
    assert res["ok"], res
    tid = res["data"]["task"]["id"]
    assert rt.call_tool("tasks__complete_task", {"task_id": tid})["data"]["task"]["status"] == "done"
    assert rt.data("tasks__task_stats")["completed"] >= 1


def test_errors_are_returned_not_raised(rt):
    assert not rt.call_tool("tasks__create_task", {"title": "x", "priority": "urgent"})["ok"]
    assert not rt.call_tool("tasks__update_task", {"task_id": 9999, "title": "y"})["ok"]
    assert not rt.call_tool("does__not_exist")["ok"]


def test_notes_documents_resources_prompts(rt):
    assert rt.call_tool("notes__create_note", {"title": "MCP", "content": "stdio transport"})["ok"]
    assert rt.data("notes__search_notes", {"query": "stdio"})["count"] == 1
    assert rt.data("documents__search_documents", {"query": "servers stdio"})["results"][0]["document"] == "arch.md"
    stats = json.loads(rt.run(rt.manager.read_resource("tasks", "tasks://stats")))
    assert "total" in stats
    assert "hours" in rt.get_prompt("tasks", "plan_my_day", {"hours_available": "3"})


def test_agent_loop_with_fake_claude(rt):
    """The loop should: call a tool, feed the result back, then return text."""
    from llm import agent as agent_mod

    calls = []

    def block(**kw):
        return NS(**kw, model_dump=lambda **_: kw)

    class FakeMessages:
        def create(self, messages, **kw):
            calls.append(messages[-1])
            if len(calls) == 1:
                return NS(stop_reason="tool_use", usage=NS(input_tokens=1, output_tokens=1),
                          content=[block(type="tool_use", id="u1", name="tasks__create_task",
                                         input={"title": "Learn LangGraph", "due_date": "2030-02-02"})])
            return NS(stop_reason="end_turn", usage=NS(input_tokens=1, output_tokens=1),
                      content=[block(type="text", text="Done — task created.")])

    agent = agent_mod.ClaudeAgent.__new__(agent_mod.ClaudeAgent)
    agent.client, agent.model = NS(messages=FakeMessages()), "fake"
    agent.tools, agent.call_tool = rt.manager.anthropic_tools(), rt.call_tool

    history = [{"role": "user", "content": "Create a task to learn LangGraph"}]
    reply = agent.chat(history)
    assert reply.text == "Done — task created."
    assert reply.traces[0].name == "tasks__create_task" and reply.traces[0].ok
    assert calls[1]["content"][0]["type"] == "tool_result"  # result was fed back to the model
    titles = [t["title"] for t in rt.data("tasks__list_tasks")["tasks"]]
    assert "Learn LangGraph" in titles
