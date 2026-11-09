"""Dashboard look & feel (soft cards, gradient accents) injected as CSS."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root{
  --bg:#F3F4F7; --card:#FFFFFF; --ink:#151821; --muted:#7A8091; --line:#E8EAF0;
  --accent:#5B5BF0; --accent2:#F472B6; --green:#22B573; --amber:#F59E0B; --red:#EF4444; --blue:#3B82F6;
  --radius:18px; --shadow:0 1px 2px rgba(16,24,40,.04), 0 4px 16px rgba(16,24,40,.04);
}
html, body, [class*="css"], .stApp, button, input, textarea { font-family:'Inter', sans-serif !important; }
.stApp { background:var(--bg); }
[data-testid="stHeader"]{ background:transparent; height:0; }
[data-testid="stToolbar"], [data-testid="stDecoration"], footer { display:none !important; }
.block-container{ padding:1.4rem 1.6rem 1rem 1.6rem !important; max-width:100% !important; }
h1,h2,h3,h4{ color:var(--ink); letter-spacing:-.01em; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"]{ background:#ECEDF1; border-right:1px solid var(--line); min-width:232px !important; max-width:232px !important; }
[data-testid="stSidebar"] .block-container, [data-testid="stSidebarContent"]{ padding-top:.4rem; }
.brand{ display:flex; align-items:center; gap:10px; font-weight:700; font-size:18px; padding:14px 6px 22px 6px; letter-spacing:.02em; }
.brand .orb{ width:22px; height:22px; border-radius:50%; background:radial-gradient(circle at 30% 30%, #A5B4FC, #6366F1 45%, #F472B6 100%); box-shadow:0 0 14px rgba(99,102,241,.55); }
.brand .g{ background:linear-gradient(90deg,#6366F1,#EC4899); -webkit-background-clip:text; color:transparent; }
[data-testid="stSidebar"] .stButton>button{
  width:100%; justify-content:flex-start; border:none; background:transparent; color:#3A3F4B;
  padding:.55rem .8rem; border-radius:12px; font-weight:500; font-size:14px; box-shadow:none;
}
[data-testid="stSidebar"] .stButton>button:hover{ background:#E1E3EA; color:var(--ink); }
[data-testid="stSidebar"] .stButton>button[kind="primary"]{
  background:linear-gradient(90deg,#C7D2FE 0%, #FBCFE8 70%, #FDA4AF 100%); color:var(--ink); font-weight:600;
}
[data-testid="stSidebar"] .stButton>button p{ font-size:14px; }
[data-testid="stSidebar"] .stButton{ width:100%; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{ gap:.3rem; }
.st-key-board .stButton>button{ padding:.1rem .55rem; font-size:12px; min-height:28px; border-radius:8px; color:#4B5162; }
.st-key-board [data-testid="stHorizontalBlock"]{ gap:.35rem; margin-bottom:10px; }
.side-sep{ height:1px; background:var(--line); margin:14px 4px; }
.srv{ display:flex; align-items:center; gap:8px; font-size:12.5px; color:#4B5162; padding:4px 8px; }
.dot{ width:8px; height:8px; border-radius:50%; display:inline-block; }
.dot.on{ background:var(--green); box-shadow:0 0 0 3px rgba(34,181,115,.15); }
.dot.off{ background:var(--red); }
.side-label{ font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); padding:0 8px 6px; }

/* ---------- top bar ---------- */
.greet{ font-size:21px; font-weight:700; color:var(--ink); padding-top:6px; }
.greet small{ display:block; font-size:12.5px; font-weight:500; color:var(--muted); margin-top:2px; }
.st-key-topsearch input{ background:#fff !important; border-radius:999px !important; border:1px solid var(--line) !important; padding-left:16px !important; height:42px; }
.st-key-topsearch [data-baseweb="input"]{ border:none !important; background:transparent !important; }
.profile{ display:flex; align-items:center; gap:10px; justify-content:flex-end; }
.bell{ width:42px; height:42px; border-radius:50%; background:#fff; display:flex; align-items:center; justify-content:center; border:1px solid var(--line); position:relative; }
.bell .badge{ position:absolute; top:9px; right:11px; width:8px; height:8px; background:var(--red); border-radius:50%; border:2px solid #fff; }
.chip-user{ display:flex; align-items:center; gap:10px; background:#fff; border:1px solid var(--line); border-radius:999px; padding:5px 16px 5px 5px; }
.avatar{ width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:14px; background:linear-gradient(135deg,#6366F1,#EC4899); flex-shrink:0; }
.chip-user b{ font-size:13.5px; color:var(--ink); display:block; line-height:1.1; }
.chip-user span{ font-size:11.5px; color:var(--muted); }

/* ---------- cards ---------- */
.card{ background:var(--card); border-radius:var(--radius); padding:16px 18px; box-shadow:var(--shadow); border:1px solid #EEF0F4; margin-bottom:14px; }
.card-h{ display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; }
.card-h .t{ display:flex; align-items:center; gap:8px; font-weight:600; font-size:15px; color:var(--ink); }
.card-h .a{ font-size:12px; color:var(--muted); }
.kpi{ background:#fff; border-radius:var(--radius); padding:16px 18px; box-shadow:var(--shadow); border:1px solid #EEF0F4; }
.kpi .l{ display:flex; gap:8px; align-items:center; font-size:14px; font-weight:500; color:#2F3441; }
.kpi .v{ font-size:30px; font-weight:600; color:var(--ink); margin:10px 0 6px; letter-spacing:-.02em; }
.kpi .d{ font-size:12.5px; color:var(--muted); display:flex; align-items:center; gap:5px; }
.tri-up{ width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:7px solid var(--green); }
.tri-down{ width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-top:7px solid var(--accent); }
.tri-warn{ width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:7px solid var(--amber); }

/* bordered streamlit containers used as cards */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) { border-radius:var(--radius); }
.st-key-chatcard{ background:linear-gradient(180deg,#F7F7FA 0%, #EFF0F4 100%); border-radius:22px; border:1px solid #E6E8EE !important; padding:14px 18px 6px 18px; box-shadow:var(--shadow); }
.st-key-taskform, .st-key-noteform, .st-key-docup, .st-key-runtool { background:#fff; border-radius:var(--radius); padding:14px 16px; border:1px solid #EEF0F4; box-shadow:var(--shadow); }

/* ---------- chat ---------- */
.persona{ display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }
.pill{ display:inline-flex; align-items:center; gap:6px; background:#E4E7F4; color:#3C4270; border-radius:999px; padding:5px 12px; font-size:12px; font-weight:500; }
.persona-r{ display:flex; align-items:center; gap:10px; }
.persona-r .orb-lg{ width:44px; height:44px; border-radius:50%; background:radial-gradient(circle at 30% 28%, #E0E7FF 0%, #818CF8 38%, #EC4899 100%); box-shadow:0 6px 20px rgba(129,140,248,.45); }
.persona-r b{ font-size:15px; display:block; color:var(--ink); }
.persona-r span{ font-size:12px; color:var(--muted); }
.msg-u{ display:flex; justify-content:flex-end; margin:10px 0; }
.msg-u div{ background:#E3E4E9; color:var(--ink); padding:10px 16px; border-radius:16px 16px 4px 16px; max-width:78%; font-size:14px; line-height:1.45; }
.bot-head{ display:flex; align-items:center; gap:10px; margin-top:8px; }
.bot-head .orb-sm{ width:28px; height:28px; border-radius:50%; background:radial-gradient(circle at 30% 28%, #E0E7FF 0%, #818CF8 40%, #EC4899 100%); flex-shrink:0; }
.bot-head span{ font-size:12px; color:var(--muted); }
[class*="st-key-bot-"]{ padding-left:38px; font-size:14px; color:var(--ink); }
[class*="st-key-bot-"] p, [class*="st-key-bot-"] li{ font-size:14px; line-height:1.55; }
[class*="st-key-bot-"] [data-testid="stExpander"]{ background:#fff; border-radius:12px; border:1px solid var(--line); }
[class*="st-key-bot-"] [data-testid="stExpander"] summary p{ font-size:12.5px; color:#4B5162; }
.trace{ font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:12px; background:#F6F7FB; border-radius:10px; padding:8px 10px; margin:6px 0; border-left:3px solid var(--green); white-space:pre-wrap; word-break:break-word; color:#30354a; }
.trace.err{ border-left-color:var(--red); }
.trace b{ color:var(--accent); }
.empty-chat{ text-align:center; padding:26px 10px 10px; color:var(--muted); }
.empty-chat h3{ color:var(--ink); font-size:20px; margin:10px 0 4px; }
.st-key-suggest .stButton>button{ background:#fff; border:1px solid var(--line); border-radius:999px; font-size:12.5px; color:#3A3F4B; padding:.35rem .9rem; }
.st-key-suggest .stButton>button:hover{ border-color:var(--accent); color:var(--accent); }
[data-testid="stChatInput"]{ border-radius:999px !important; background:#fff; border:1px solid var(--line); }
[data-testid="stChatInput"] textarea{ font-size:14px !important; }

/* ---------- right panels ---------- */
.ev{ display:flex; align-items:center; gap:10px; padding:9px 0; border-bottom:1px dashed #EEF0F4; font-size:13px; }
.ev:last-child{ border-bottom:none; }
.ev .bar{ width:3px; align-self:stretch; border-radius:3px; background:var(--accent); }
.ev .n{ flex:1; color:var(--ink); font-weight:500; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.ev .n small{ display:block; color:var(--muted); font-weight:400; font-size:11.5px; }
.ev .w{ color:#4B5162; font-size:12px; white-space:nowrap; }
.tag{ font-size:10.5px; padding:2px 8px; border-radius:999px; font-weight:600; white-space:nowrap; }
.tag.high{ background:#FDECEC; color:#C53030; } .tag.medium{ background:#FEF3DC; color:#B45309; } .tag.low{ background:#E7F7EF; color:#16794C; }
.tag.todo{ background:#EEF0F7; color:#4B5162; } .tag.in_progress{ background:#E6EEFF; color:#2F5BD3; } .tag.done{ background:#E7F7EF; color:#16794C; }
.today{ font-size:12px; color:var(--muted); margin:-4px 0 6px; }
.today i{ color:var(--red); font-style:normal; }
.prog{ margin:10px 0 12px; }
.prog .h{ display:flex; justify-content:space-between; font-size:12.5px; color:#2F3441; margin-bottom:6px; }
.prog .track{ height:6px; background:#EEF0F4; border-radius:6px; overflow:hidden; }
.prog .fill{ height:100%; border-radius:6px; }
.act{ display:flex; gap:10px; align-items:center; background:#F6F7FA; border-radius:12px; padding:9px 10px; margin-bottom:8px; }
.act .ic{ width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.act .m{ font-size:12.5px; color:var(--ink); line-height:1.3; }
.act .m small{ display:block; color:var(--muted); font-size:11px; margin-top:2px; }

/* ---------- task board / notes ---------- */
.col-h{ display:flex; align-items:center; gap:8px; font-weight:600; font-size:14px; margin-bottom:8px; color:var(--ink); }
.col-h .count{ background:#E4E6EE; color:#4B5162; border-radius:999px; padding:1px 8px; font-size:11.5px; }
.tcard{ background:#fff; border-radius:14px; padding:12px 14px; border:1px solid #EEF0F4; box-shadow:var(--shadow); margin-bottom:6px; }
.tcard .tt{ font-weight:600; font-size:13.5px; color:var(--ink); margin-bottom:6px; }
.tcard .meta{ display:flex; gap:6px; flex-wrap:wrap; align-items:center; font-size:11.5px; color:var(--muted); }
.tcard.done .tt{ text-decoration:line-through; color:var(--muted); }
.ncard{ background:#fff; border-radius:16px; padding:14px 16px; border:1px solid #EEF0F4; box-shadow:var(--shadow); margin-bottom:12px; min-height:150px; }
.ncard .tt{ font-weight:600; font-size:14.5px; color:var(--ink); display:flex; justify-content:space-between; gap:8px; }
.ncard p{ font-size:13px; color:#4B5162; white-space:pre-wrap; margin:8px 0; line-height:1.45; }
.ncard .tags span{ font-size:11px; background:#EEF0FB; color:#4F46E5; padding:2px 8px; border-radius:999px; margin-right:4px; }
.star{ color:var(--amber); }
.hit{ background:#fff; border-radius:12px; border:1px solid #EEF0F4; padding:10px 14px; margin-bottom:8px; font-size:13px; }
.hit b{ color:var(--accent); font-size:12px; }
.page-title{ font-size:22px; font-weight:700; color:var(--ink); margin:4px 0 2px; }
.page-sub{ font-size:13px; color:var(--muted); margin-bottom:14px; }
.stButton>button{ border-radius:10px; font-size:13px; }
.stButton>button[kind="primary"]{ background:linear-gradient(90deg,#6366F1,#8B5CF6); border:none; }
.mcp-row{ display:grid; grid-template-columns:150px 1fr; gap:10px; font-size:13px; padding:8px 0; border-bottom:1px solid #F0F1F5; }
code{ font-size:12px !important; }
</style>
"""
