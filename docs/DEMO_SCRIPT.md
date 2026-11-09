# 2-minute demo video script

**0:00 – Hook (dashboard on screen)**
"Most AI chatbots only answer questions. This one *acts*. It manages my tasks, notes and
documents through the Model Context Protocol."

**0:15 – Architecture (show README diagram)**
"Streamlit is the MCP host. It connects to three MCP servers over stdio: tasks on SQLite, notes as
Markdown files, and a document search server. Claude decides which tool to use; MCP executes it."

**0:35 – Live: create a task**
Type: *"Create a high-priority task to learn LangGraph tomorrow in the Learning project."*
Open the "MCP · tool calls" panel → point at `tasks__create_task` and its arguments.
Point at the Upcoming card and the Activity Feed updating.

**0:55 – Live: multi-tool reasoning**
Type: *"Give me my daily brief."* → Claude calls `list_tasks`, `task_stats`, `search_notes`.
"One request, three tool calls across two servers."

**1:15 – Live: documents**
Type: *"Explain my project architecture."* → `search_documents` → answer cites the file.

**1:30 – MCP Inspector page**
"Every tool is discovered at runtime with its JSON schema. Here I call one by hand, and here are
the server-side prompts."

**1:45 – Close**
"Built with the official MCP Python SDK, the Claude API, Streamlit, SQLite and Pydantic, with
15 tests. Next: RAG over documents and a remote HTTP transport. Code on GitHub. Link below."
