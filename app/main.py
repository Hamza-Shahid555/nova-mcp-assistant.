"""Streamlit MCP Host — the app the user talks to.

Run:  streamlit run app/main.py

Every piece of data on screen comes through MCP: the dashboard calls the
same tools Claude uses (task_stats, list_tasks, search_notes, ...). The UI
is just another MCP client of the servers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make project packages importable

import streamlit as st  # noqa: E402

from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ASSISTANT_NAME, DOCUMENTS_DIR, USER_NAME  # noqa: E402
from mcp_client.runtime import MCPRuntime  # noqa: E402
from ui import components as C  # noqa: E402
from ui.styles import CSS  # noqa: E402

st.set_page_config(page_title=f"{ASSISTANT_NAME} · MCP Productivity", page_icon="✦", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------- runtime
@st.cache_resource(show_spinner="Starting MCP servers…")
def get_runtime() -> MCPRuntime:
    return MCPRuntime()


rt = get_runtime()
mgr = rt.manager
assert mgr is not None

ss = st.session_state
ss.setdefault("page", "Dashboard")
ss.setdefault("chat", [])      # what we display: {"role", "text", "traces"}
ss.setdefault("history", [])   # what we send to Claude (Anthropic message format)

PAGES = [("Dashboard", "◧"), ("Tasks", "☑"), ("Notes", "✎"), ("Documents", "▤"), ("MCP Inspector", "⌬")]


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f'<div class="brand"><div class="orb"></div><span>DAILY <span class="g">AI</span></span></div>',
                unsafe_allow_html=True)
    if st.button("＋  New Chat", key="nav-new"):
        ss.chat, ss.history, ss.page = [], [], "Dashboard"
        st.rerun()
    for name, glyph in PAGES:
        if st.button(f"{glyph}  {name}", key=f"nav-{name}", type="primary" if ss.page == name else "secondary"):
            ss.page = name
            st.rerun()
    st.markdown('<div class="side-sep"></div><div class="side-label">MCP servers</div>', unsafe_allow_html=True)
    for s in mgr.status.values():
        st.markdown(f'<div class="srv"><span class="dot {"on" if s.connected else "off"}"></span>'
                    f'{s.name}<span style="margin-left:auto;color:#7A8091">{len(s.tools)} tools</span></div>',
                    unsafe_allow_html=True)
    st.markdown(f'<div class="side-sep"></div><div class="side-label">Model</div>'
                f'<div class="srv">{C.esc(ANTHROPIC_MODEL)}</div>', unsafe_allow_html=True)
    if not ANTHROPIC_API_KEY:
        st.warning("Add ANTHROPIC_API_KEY to .env to enable chat.", icon="🔑")


# ---------------------------------------------------------------- helpers
def refresh_data() -> dict:
    return {
        "stats": rt.data("tasks__task_stats"),
        "open": rt.data("tasks__list_tasks", {"status": "open"}).get("tasks", []),
        "activity": rt.data("tasks__recent_activity", {"limit": 6}).get("activity", []),
        "notes": rt.data("notes__search_notes", {"query": "", "limit": 50}).get("notes", []),
    }


def run_agent(prompt: str) -> None:
    """Send one user message through Claude + MCP tools."""
    from llm.agent import ClaudeAgent

    ss.chat.append({"role": "user", "text": prompt})
    ss.history.append({"role": "user", "content": prompt})
    try:
        agent = ClaudeAgent(tools=mgr.anthropic_tools(), call_tool=rt.call_tool)
        reply = agent.chat(ss.history)
        ss.chat.append({"role": "assistant", "text": reply.text,
                        "traces": [t.__dict__ for t in reply.traces], "usage": reply.usage})
    except Exception as e:  # noqa: BLE001 — show any API/network error in the chat
        ss.history.pop()  # keep history valid for the next turn
        ss.chat.append({"role": "assistant", "text": f"**Error:** {e}", "traces": [], "error": True})


def render_chat(height: int) -> None:
    connected = sum(s.connected for s in mgr.status.values())
    with st.container(key="chatcard"):
        st.markdown(
            f'<div class="persona"><span class="pill">{C.icon("plug", "#3C4270", 14)} {connected} MCP servers · '
            f'{len(mgr.tools)} tools</span><div class="persona-r"><div style="text-align:right"><b>{ASSISTANT_NAME}</b>'
            f'<span>AI Assistant</span></div><div class="orb-lg"></div></div></div>', unsafe_allow_html=True)
        box = st.container(height=height, border=False)
        with box:
            if not ss.chat:
                st.markdown(f'<div class="empty-chat">{C.icon("spark", "#8B5CF6", 40)}<h3>Hi! I\'m {ASSISTANT_NAME}</h3>'
                            'I manage your tasks, search your notes and explain your documents — all through MCP tools.</div>',
                            unsafe_allow_html=True)
                with st.container(key="suggest", horizontal=True, horizontal_alignment="center"):
                    for s in ["Give me my daily brief", "Show my pending tasks",
                              "Create a task to learn LangGraph tomorrow", "Find my important notes about RAG",
                              "Explain my project architecture"]:
                        if st.button(s, key=f"sg-{s}"):
                            ss.pending = s
                            st.rerun()
            for i, m in enumerate(ss.chat):
                if m["role"] == "user":
                    st.markdown(f'<div class="msg-u"><div>{C.esc(m["text"])}</div></div>', unsafe_allow_html=True)
                    continue
                st.markdown(f'<div class="bot-head"><div class="orb-sm"></div><span>{ASSISTANT_NAME}</span></div>',
                            unsafe_allow_html=True)
                with st.container(key=f"bot-{i}"):
                    st.markdown(m["text"])
                    if m.get("traces"):
                        with st.expander(f"MCP · {len(m['traces'])} tool call(s)"):
                            for t in m["traces"]:
                                out = t["output"] if len(t["output"]) < 700 else t["output"][:700] + " …"
                                st.markdown(f'<div class="trace {"" if t["ok"] else "err"}"><b>{C.esc(t["name"])}</b>'
                                            f'  {t["ms"]} ms\nargs: {C.esc(json.dumps(t["arguments"]))}\n'
                                            f'→ {C.esc(out)}</div>', unsafe_allow_html=True)
            if ss.get("pending"):
                st.markdown(f'<div class="msg-u"><div>{C.esc(ss.pending)}</div></div>', unsafe_allow_html=True)
                with st.spinner("Thinking…"):
                    run_agent(ss.pop("pending"))
                st.rerun()
        prompt = st.chat_input(f"Ask {ASSISTANT_NAME} anything…", disabled=not ANTHROPIC_API_KEY)
        if prompt:
            ss.pending = prompt
            st.rerun()


def top_bar() -> str:
    c1, c2, c3 = st.columns([1.25, 1.6, 1.15], vertical_alignment="center")
    c1.markdown(f'<div class="greet">{C.greeting()}, {C.esc(USER_NAME)}<small>Here\'s what is happening today</small></div>',
                unsafe_allow_html=True)
    q = c2.text_input("search", placeholder="⌕  Search task, project, notes, documents",
                      label_visibility="collapsed", key="topsearch")
    c3.markdown(f'<div class="profile"><div class="bell">{C.icon("bell", "#151821", 18)}<span class="badge"></span></div>'
                f'<div class="chip-user"><div class="avatar">{C.esc(USER_NAME[:1])}</div><div><b>{C.esc(USER_NAME)}</b>'
                f'<span>AI Engineer</span></div></div></div>', unsafe_allow_html=True)
    return q.strip()


def search_results(q: str) -> None:
    tasks = [t for t in rt.data("tasks__list_tasks").get("tasks", [])
             if q.lower() in f'{t["title"]} {t["project"]} {t["description"]}'.lower()]
    notes = rt.data("notes__search_notes", {"query": q, "limit": 5}).get("notes", [])
    docs = rt.data("documents__search_documents", {"query": q, "top_k": 3}).get("results", [])
    body = "".join(f'<div class="hit"><b>TASK</b> · {C.esc(t["title"])} <span class="tag {t["status"]}">'
                   f'{t["status"]}</span></div>' for t in tasks[:5])
    body += "".join(f'<div class="hit"><b>NOTE</b> · {C.esc(n["title"])} — {C.esc(n["preview"][:90])}</div>' for n in notes)
    body += "".join(f'<div class="hit"><b>DOC</b> · {C.esc(d["document"])} — {C.esc(d["text"][:120])}…</div>' for d in docs)
    st.markdown(C.card(f'Results for “{q}”', "spark", body or '<div class="today">No matches.</div>',
                       f"{len(tasks) + len(notes) + len(docs)} found"), unsafe_allow_html=True)


# ================================================================= pages
def page_dashboard() -> None:
    q = top_bar()
    st.write("")
    data = refresh_data()
    s = data["stats"]
    main, right = st.columns([2.55, 1], gap="medium")
    with main:
        if q:
            search_results(q)
        k = st.columns(4, gap="small")
        k[0].markdown(C.kpi("Tasks Today", s.get("due_today", 0), f'{s.get("due_this_week", 0)} due this week',
                            "task", "#6366F1", "down"), unsafe_allow_html=True)
        k[1].markdown(C.kpi("In Progress", s.get("in_progress", 0), f'{s.get("todo", 0)} still to do',
                            "progress", "#F59E0B", "warn"), unsafe_allow_html=True)
        k[2].markdown(C.kpi("Completed", s.get("completed", 0), f'{s.get("completed_today", 0)} completed today',
                            "check", "#22B573", "up"), unsafe_allow_html=True)
        k[3].markdown(C.kpi("Overdue", s.get("overdue", 0), f'{sum(n["important"] for n in data["notes"])} important notes',
                            "alert", "#EF4444", "warn" if s.get("overdue") else "up"), unsafe_allow_html=True)
        st.write("")
        render_chat(height=430)
    with right:
        st.markdown(C.card("Upcoming", "calendar", C.upcoming_body(data["open"]), f'{len(data["open"])} open'),
                    unsafe_allow_html=True)
        st.markdown(C.card("Project Progress", "chart", C.progress_body(s.get("projects", {})), "by tasks done"),
                    unsafe_allow_html=True)
        st.markdown(C.card("Activity Feed", "feed", C.activity_body(data["activity"]), "live"), unsafe_allow_html=True)


def page_tasks() -> None:
    st.markdown('<div class="page-title">Tasks</div><div class="page-sub">Every button here calls a tool on the '
                '<b>tasks</b> MCP server — the same tools Claude uses.</div>', unsafe_allow_html=True)
    with st.expander("＋ Add task", expanded=False):
        with st.form("add_task", clear_on_submit=True, border=False):
            a, b, c, d = st.columns([2.4, 1, 1, 1.2])
            title = a.text_input("Title")
            prio = b.selectbox("Priority", ["medium", "high", "low"])
            due = c.date_input("Due", value=None)
            proj = d.text_input("Project", value="General")
            if st.form_submit_button("Create task", type="primary"):
                res = rt.call_tool("tasks__create_task", {"title": title, "priority": prio, "project": proj,
                                                          "due_date": due.isoformat() if due else None})
                (st.toast("Task created") if res["ok"] else st.error(res["text"]))
    tasks = rt.data("tasks__list_tasks").get("tasks", [])
    projects = sorted({t["project"] for t in tasks})
    pf = st.segmented_control("Project", ["All", *projects], default="All", label_visibility="collapsed")
    if pf and pf != "All":
        tasks = [t for t in tasks if t["project"] == pf]
    board = st.container(key="board")
    cols = board.columns(3, gap="medium")
    for col, (status, label) in zip(cols, [("todo", "To do"), ("in_progress", "In progress"), ("done", "Done")]):
        group = [t for t in tasks if t["status"] == status]
        col.markdown(f'<div class="col-h">{label}<span class="count">{len(group)}</span></div>', unsafe_allow_html=True)
        for t in group:
            col.markdown(C.task_card(t), unsafe_allow_html=True)
            row = col.container(horizontal=True, gap="small")
            action = None
            if status == "todo" and row.button("Start", key=f"s{t['id']}"):
                action = ("tasks__update_task", {"task_id": t["id"], "status": "in_progress"})
            if status != "done" and row.button("Done", key=f"d{t['id']}"):
                action = ("tasks__complete_task", {"task_id": t["id"]})
            if status == "done" and row.button("Reopen", key=f"r{t['id']}"):
                action = ("tasks__update_task", {"task_id": t["id"], "status": "todo"})
            if row.button("Delete", key=f"x{t['id']}"):
                action = ("tasks__delete_task", {"task_id": t["id"]})
            if action:
                rt.call_tool(*action)
                st.rerun()


def page_notes() -> None:
    st.markdown('<div class="page-title">Notes</div><div class="page-sub">Markdown files in <code>data/notes/</code>, '
                'served by the <b>notes</b> MCP server.</div>', unsafe_allow_html=True)
    a, b = st.columns([3, 1], vertical_alignment="bottom")
    q = a.text_input("Search notes", placeholder="e.g. RAG chunking")
    imp = b.toggle("Important only")
    with st.expander("＋ New note"):
        with st.form("add_note", clear_on_submit=True, border=False):
            t = st.text_input("Title")
            body = st.text_area("Content (Markdown)", height=140)
            c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
            tags = c1.text_input("Tags (comma separated)")
            important = c2.checkbox("Important")
            if st.form_submit_button("Save note", type="primary"):
                res = rt.call_tool("notes__create_note", {"title": t, "content": body, "important": important,
                                                          "tags": [x.strip() for x in tags.split(",") if x.strip()]})
                (st.toast("Note saved") if res["ok"] else st.error(res["text"]))
    notes = rt.data("notes__search_notes", {"query": q, "important_only": imp, "limit": 50}).get("notes", [])
    cols = st.columns(3, gap="medium")
    for i, n in enumerate(notes):
        with cols[i % 3]:
            st.markdown(C.note_card(n), unsafe_allow_html=True)
            with st.popover("Open", use_container_width=True):
                full = rt.data("notes__get_note", {"note_id": n["id"]}).get("note", {})
                st.markdown(f"### {full.get('title', '')}\n\n{full.get('content', '')}")
    if not notes:
        st.info("No notes found.")


def page_documents() -> None:
    st.markdown('<div class="page-title">Documents</div><div class="page-sub">TXT / Markdown / PDF files in '
                '<code>data/documents/</code>, searched by the <b>documents</b> MCP server.</div>', unsafe_allow_html=True)
    left, right = st.columns([1, 1.6], gap="large")
    with left:
        with st.container(key="docup"):
            up = st.file_uploader("Add documents", type=["txt", "md", "pdf"], accept_multiple_files=True)
            if up and st.button("Save to library", type="primary"):
                for f in up:
                    (DOCUMENTS_DIR / Path(f.name).name).write_bytes(f.getvalue())
                st.toast(f"Saved {len(up)} file(s)")
        docs = rt.data("documents__list_documents").get("documents", [])
        st.markdown(C.card("Library", "note", "".join(
            f'<div class="ev"><div class="n">{C.esc(d["name"])}<small>{d["type"].upper()} · {d["size_kb"]} KB</small></div></div>'
            for d in docs) or '<div class="today">No documents yet.</div>', f"{len(docs)} files"), unsafe_allow_html=True)
    with right:
        q = st.text_input("Search passages", placeholder="e.g. request flow")
        if q:
            hits = rt.data("documents__search_documents", {"query": q, "top_k": 5}).get("results", [])
            for h in hits:
                st.markdown(f'<div class="hit"><b>{C.esc(h["document"])}</b> · score {h["score"]}<br>'
                            f'{C.esc(h["text"][:500])}</div>', unsafe_allow_html=True)
            if not hits:
                st.info("No matching passages.")


def page_inspector() -> None:
    st.markdown('<div class="page-title">MCP Inspector</div><div class="page-sub">What the host discovered over the '
                'protocol: servers, tools (with JSON schemas), resources and prompts. Call any tool by hand.</div>',
                unsafe_allow_html=True)
    cols = st.columns(len(mgr.status))
    for col, s in zip(cols, mgr.status.values()):
        body = (f'<div class="mcp-row"><span>Status</span><span><span class="dot {"on" if s.connected else "off"}"></span> '
                f'{"connected" if s.connected else C.esc(s.error)}</span></div>'
                f'<div class="mcp-row"><span>Tools</span><span>{", ".join(s.tools)}</span></div>'
                f'<div class="mcp-row"><span>Resources</span><span>{", ".join(s.resources) or "—"}</span></div>'
                f'<div class="mcp-row"><span>Prompts</span><span>{", ".join(s.prompts) or "—"}</span></div>')
        col.markdown(C.card(s.name, "plug", body, "stdio"), unsafe_allow_html=True)
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        with st.container(key="runtool"):
            name = st.selectbox("Tool", list(mgr.tools))
            info = mgr.tools[name]
            st.caption(info.description)
            with st.expander("Input schema"):
                st.json(info.input_schema)
            example = {k: v.get("default", "") for k, v in info.input_schema.get("properties", {}).items()
                       if k in info.input_schema.get("required", [])}
            args = st.text_area("Arguments (JSON)", value=json.dumps(example, indent=2), height=120)
            if st.button("Call tool", type="primary"):
                try:
                    res = rt.call_tool(name, json.loads(args or "{}"))
                    (st.success if res["ok"] else st.error)(f'{res["ms"]} ms')
                    st.json(res.get("data") or res["text"])
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON: {e}")
    with right:
        st.markdown("**Prompts** — reusable workflows exposed by servers")
        for s in mgr.status.values():
            for p in s.prompts:
                if st.button(f"{s.name} › {p}", key=f"p-{s.name}-{p}", use_container_width=True):
                    ss.pending = rt.get_prompt(s.name, p, {"topic": "RAG"} if p == "study_plan" else {})
                    ss.page = "Dashboard"
                    st.rerun()
        st.caption("Clicking a prompt fetches it from the server (prompts/get) and sends it to the chat.")


{"Dashboard": page_dashboard, "Tasks": page_tasks, "Notes": page_notes,
 "Documents": page_documents, "MCP Inspector": page_inspector}[ss.page]()
