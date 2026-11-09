# Learning guide — build it again in your head, phase by phase

The whole app is already working. Use this guide to *understand* it. For each phase: read the
files, run the check, do the exercise, and make sure you can explain it in your own words
before moving on.

---

## Phase 1 — Architecture & structure

**What:** a modular layout where each layer has one job.

| Layer | Folder | Knows about MCP? |
|---|---|---|
| Storage | `database/` | No: plain Python + SQLite |
| MCP servers | `servers/` | Yes: wraps storage as tools/resources/prompts |
| MCP client | `mcp_client/` | Yes: connects, discovers, routes |
| LLM | `llm/` | No: only sees tool *schemas* and a `call_tool` function |
| UI / Host | `app/`, `ui/` | Uses the client |

**Why:** you can test storage without MCP, swap Claude for another model without touching servers,
and reuse the servers in Claude Desktop.

**Exercise:** draw the request flow for "Show my pending tasks" from memory, naming every file it passes through.

---

## Phase 2 — Database & validation (`database/`)

- `models.py`: Pydantic models. `TaskCreate(priority="urgent")` raises a `ValidationError`. This is your first line of defence against bad LLM output.
- `db.py`: `TaskRepository`. Note `_conn()` is a **context manager** (`@contextmanager`) that commits and always closes the connection.
- `update()` uses `model_dump(exclude_unset=True)` so only fields you passed change.

**Check:** `python -m pytest tests/test_storage.py -v`

**Exercise:** add a `tags` column to tasks (schema, model, repository) and a test for it.

---

## Phase 3 — Your first MCP server (`servers/tasks_server.py`)

```python
from mcp.server.mcpserver import MCPServer   # SDK v2 (was FastMCP in v1)
mcp = MCPServer(name="tasks")

@mcp.tool()
def create_task(title: str, priority: Literal["low","medium","high"] = "medium", ...) -> dict:
    """Docstring becomes the tool description the LLM reads."""
```

- The **decorator** registers the function. The SDK turns the **type hints** into a JSON Schema and the **docstring** into the description. Good docstrings make the LLM call the tool correctly.
- `@mcp.resource("tasks://stats")` is read-only data addressed by URI. `@mcp.prompt()` is a reusable instruction template.
- `mcp.run()` defaults to the **stdio** transport: JSON-RPC messages over stdin/stdout. That is why servers must **never `print()`**. Log to stderr instead.
- Tools return `{"ok": False, "error": ...}` instead of raising, so the model gets a readable reason and can retry.

**Check:** `mcp dev servers/tasks_server.py` opens the official inspector. Call `create_task` by hand.

**Exercise:** add a `search_tasks(query)` tool. Restart the app and confirm it appears in the MCP Inspector page with no client changes. That is tool discovery at work.

---

## Phase 4 — The MCP client (`mcp_client/manager.py`, `runtime.py`)

The connection sequence for each server:

```
stdio_client(params)        -> spawn `python -m servers.tasks_server`, get (read, write) streams
ClientSession(read, write)  -> JSON-RPC session over those streams
session.initialize()        -> handshake: protocol version + capabilities
session.list_tools()        -> discovery: names, descriptions, input schemas
session.call_tool(name, args)
```

- `AsyncExitStack` keeps many async context managers open and closes them all together.
- Tools are stored as `server__tool` so two servers can't clash.
- Only a few environment variables reach the subprocess, so `_params()` forwards `DATA_DIR` etc. explicitly. (The tests rely on this.)
- `runtime.py`: Streamlit is synchronous and reruns on every click. We run **one asyncio loop in a background thread** and submit coroutines with `asyncio.run_coroutine_threadsafe`. The manager is entered and exited inside a single owner task because anyio requires it.

**Check:** `python -m pytest tests/test_mcp_integration.py -v`

**Exercise:** stop one server from starting (e.g. typo in its module name in `SERVERS`). What happens in the sidebar and the Inspector? Why doesn't the app crash?

---

## Phase 5 — Claude + the tool-calling loop (`llm/agent.py`)

```
messages + tools ─▶ Claude
          ◀─ stop_reason="tool_use", content=[tool_use{id,name,input}]
call MCP tool(s)
messages += assistant content, user [tool_result{tool_use_id, content, is_error}]
          ─▶ Claude … until stop_reason != "tool_use"
```

- `mgr.anthropic_tools()` converts MCP tool schemas into Claude's `tools=[...]` format. **This adapter is where MCP meets the LLM.**
- Every `tool_result` must reference the `tool_use_id` it answers.
- `MAX_TOOL_ROUNDS` stops infinite loops.
- The system prompt tells Claude today's date and to look up ids before updating.

**Check:** `python -m app.cli`. Watch the `-> tasks__...` lines as Claude works.

**Exercise:** ask "complete the LangGraph task". Count the tool calls and explain why there are two (`list_tasks` then `complete_task`).

---

## Phase 6 — Notes & Documents servers

- Notes are Markdown files with a small header (`database/notes_store.py`). `notes://{note_id}` is a **resource template**.
- Documents (`database/doc_search.py`): paragraph chunks + TF-IDF scoring. This is the place to add embeddings/RAG **later**.
- Both check paths so `../../secret` can't escape the data folder.

**Exercise:** add `.docx` support to `read_text()` using `python-docx`.

---

## Phase 7 — Streamlit dashboard (`app/main.py`, `ui/`)

- `@st.cache_resource` creates the `MCPRuntime` **once** per process, so servers aren't respawned on each rerun.
- The dashboard is just another MCP client: KPI cards call `task_stats`, the Kanban buttons call `update_task`, and so on.
- Styling is plain CSS (`ui/styles.py`). `st.container(key="chatcard")` gives the element a CSS class `st-key-chatcard` to target.
- Chat flow: input → `ss.pending` → rerun → spinner → `run_agent()` → rerun.

**Exercise:** add a fifth KPI card "Notes" using `notes__search_notes`.

---

## Phase 8 — Testing, security, docs

- 15 tests: unit (storage, components) + integration (real servers over stdio + the Claude loop with a fake model, so no API cost).
- Secrets in `.env`, input validation, path checks, escaped HTML, capped loops, stderr logging.

**Exercise:** write a test proving `delete_task` on a missing id returns `ok: false`.

---

## Concepts you can now explain

- MCP Host vs Client vs Server, and why one client session exists per server
- Tools vs Resources vs Prompts
- stdio transport and JSON-RPC; why stdout must stay clean
- Tool discovery (`tools/list`) and how schemas come from type hints
- How an LLM chooses a tool, and the difference between native tool calling and MCP
- Multi-server routing, error handling and graceful degradation
- Bridging async protocol code into a synchronous UI framework
