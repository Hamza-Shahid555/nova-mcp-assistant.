"""Small HTML builders for the dashboard cards. Pure functions -> easy to test."""

from __future__ import annotations

import html
from datetime import date, datetime

_ICON_PATHS = {
    "task": '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 9h8M8 13h5"/><path d="m14 17 2 2 4-4"/>',
    "progress": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "check": '<path d="m4 12 5 5L20 6"/>',
    "alert": '<path d="M12 3 2 20h20L12 3z"/><path d="M12 10v4M12 17h.01"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "chart": '<path d="M12 3a9 9 0 1 0 9 9h-9z"/>',
    "feed": '<path d="M4 6h16M4 12h10M4 18h7"/>',
    "bell": '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    "spark": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
    "note": '<path d="M5 4h10l4 4v12H5z"/><path d="M15 4v4h4M8 12h8M8 16h5"/>',
    "plug": '<path d="M9 7V3M15 7V3M7 7h10v4a5 5 0 0 1-10 0z"/><path d="M12 16v5"/>',
}


def icon(name: str, color: str = "#5B5BF0", size: int = 18) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">{_ICON_PATHS[name]}</svg>')


def esc(s: object) -> str:
    return html.escape(str(s))


def greeting(now: datetime | None = None) -> str:
    h = (now or datetime.now()).hour
    return "Good Morning" if h < 12 else "Good Afternoon" if h < 17 else "Good Evening"


def due_label(due: str | None) -> str:
    if not due:
        return "No date"
    d = date.fromisoformat(due)
    delta = (d - date.today()).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    if delta == -1:
        return "Yesterday"
    if delta < 0:
        return f"{-delta}d overdue"
    if delta < 7:
        return d.strftime("%a")
    return d.strftime("%b %d")


def kpi(label: str, value: object, sub: str, icon_name: str, color: str, trend: str = "up") -> str:
    tri = {"up": "tri-up", "down": "tri-down", "warn": "tri-warn"}[trend]
    return (f'<div class="kpi"><div class="l">{icon(icon_name, color)} {esc(label)}</div>'
            f'<div class="v">{esc(value)}</div><div class="d"><span class="{tri}"></span>{esc(sub)}</div></div>')


def card(title: str, icon_name: str, body: str, action: str = "") -> str:
    return (f'<div class="card"><div class="card-h"><div class="t">{icon(icon_name, "#151821", 17)} {esc(title)}</div>'
            f'<div class="a">{esc(action)}</div></div>{body}</div>')


BAR_COLORS = ["#22B573", "#8B5CF6", "#F59E0B", "#3B82F6", "#EC4899", "#14B8A6"]
PRIO_COLOR = {"high": "#EF4444", "medium": "#F59E0B", "low": "#22B573"}


def upcoming_body(tasks: list[dict], limit: int = 5) -> str:
    today = date.today()
    head = f'<div class="today">Today <i>●</i> {today.strftime("%B %d, %Y")}</div>'
    rows = []
    for t in tasks[:limit]:
        rows.append(
            f'<div class="ev"><div class="bar" style="background:{PRIO_COLOR[t["priority"]]}"></div>'
            f'<div class="n">{esc(t["title"])}<small>{esc(t["project"])}</small></div>'
            f'<div class="w">{esc(due_label(t["due_date"]))}</div>'
            f'<span class="tag {t["priority"]}">{t["priority"]}</span></div>')
    return head + ("".join(rows) or '<div class="today">Nothing scheduled. Ask the assistant to add a task.</div>')


def progress_body(projects: dict) -> str:
    out = []
    for i, (name, p) in enumerate(sorted(projects.items(), key=lambda kv: -kv[1]["total"])[:5]):
        c = BAR_COLORS[i % len(BAR_COLORS)]
        out.append(f'<div class="prog"><div class="h"><span>{esc(name)}</span><span>{p["pct"]}%</span></div>'
                   f'<div class="track"><div class="fill" style="width:{p["pct"]}%;background:{c}"></div></div></div>')
    return "".join(out) or '<div class="today">No projects yet.</div>'


def ago(ts: str) -> str:
    try:
        secs = (datetime.now() - datetime.fromisoformat(ts)).total_seconds()
    except ValueError:
        return ""
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


def activity_body(items: list[dict], limit: int = 4) -> str:
    out = []
    for a in items[:limit]:
        done = a["message"].startswith("Completed")
        src_icon = "check" if done else ("note" if a["source"] == "notes" else "task")
        bg = "#22B573" if done else ("#F59E0B" if a["source"] == "notes" else "#6366F1")
        out.append(f'<div class="act"><div class="ic" style="background:{bg}">{icon(src_icon, "#fff", 14)}</div>'
                   f'<div class="m">{esc(a["message"])}<small>{ago(a["created_at"])} · {esc(a["source"])} server</small></div></div>')
    return "".join(out) or '<div class="today">No activity yet.</div>'


def task_card(t: dict) -> str:
    return (f'<div class="tcard {"done" if t["status"] == "done" else ""}"><div class="tt">{esc(t["title"])}</div>'
            f'<div class="meta"><span class="tag {t["priority"]}">{t["priority"]}</span>'
            f'<span>{esc(t["project"])}</span><span>· {esc(due_label(t["due_date"]))}</span><span>· #{t["id"]}</span></div></div>')


def note_card(n: dict) -> str:
    tags = "".join(f"<span>{esc(t)}</span>" for t in n.get("tags", []))
    star = '<span class="star">★</span>' if n.get("important") else ""
    body = n.get("preview", n.get("content", ""))
    return (f'<div class="ncard"><div class="tt">{esc(n["title"])}{star}</div><p>{esc(body)}</p>'
            f'<div class="tags">{tags}</div></div>')
