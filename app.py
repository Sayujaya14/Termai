import os
import queue
import threading
import time

import streamlit as st

from agent import run_agent
from auth import (
    get_current_user_id,
    is_logged_in,
    logout_session,
    render_login_page,
)
from memory import get_all_tasks
from paths import run_startup_migrations, user_workspace_root
from skills import list_skills

st.set_page_config(
    page_title="Termai",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* Hide menu/footer only — keep header so sidebar open/close works */
#MainMenu, footer { visibility: hidden; height: 0 !important; }
header[data-testid="stHeader"] {
    visibility: visible !important;
    background: #000000 !important;
}
[data-testid="stSidebarCollapsedControl"],
button[data-testid="stExpandSidebarButton"],
[data-testid="stSidebar"] button[kind="header"] {
    visibility: visible !important;
    display: flex !important;
    color: #ffffff !important;
    background: #222 !important;
    border: 1px solid #444 !important;
    border-radius: 6px !important;
    z-index: 10001 !important;
}
.block-container { padding-top: 1rem !important; padding-bottom: 0 !important; }

.stApp { background-color: #000000 !important; }
[data-testid="stSidebar"] {
    background-color: #000000 !important;
    border-right: 1px solid #222;
    min-width: 16rem !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stRadio label {
    color: #cdd6f4 !important;
}

.line-tool     { color: #89b4fa; margin: 2px 0; font-family: monospace; font-size: 13px; }
.line-output   { color: #a6e3a1; margin: 1px 0; font-family: monospace; font-size: 13px; padding-left: 16px; }
.line-done     { color: #a6e3a1; font-weight: bold; margin: 6px 0 2px 0; font-family: monospace; font-size: 13px; }
.line-skill    { color: #f9e2af; margin: 2px 0; font-family: monospace; font-size: 13px; }
.line-thinking { color: #cba6f7; margin: 2px 0; font-family: monospace; font-size: 13px; }
.line-task     { color: #ffffff; font-weight: bold; margin: 8px 0 6px 0; font-family: monospace; font-size: 14px; border-bottom: 1px solid #333; padding-bottom: 6px; }
.line-error    { color: #f38ba8; margin: 2px 0; font-family: monospace; font-size: 13px; }

.terminal-wrap {
    background: #0d0d0d;
    border-radius: 8px;
    border: 1px solid #222;
    padding: 16px;
    min-height: 72vh;
    max-height: 72vh;
    overflow-y: auto;
}

.input-wrap {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #000000;
    border-top: 1px solid #222;
    padding: 12px 24px;
    z-index: 99;
}

div[data-testid="stTextInput"] input {
    background: #111111 !important;
    color: #cdd6f4 !important;
    border: 1px solid #444 !important;
    border-radius: 6px !important;
    font-family: monospace !important;
    font-size: 14px !important;
}
div[data-testid="stTextInput"] input::placeholder {
    color: #ffffff !important;
    opacity: 1 !important;
}
div[data-testid="stTextInput"] input::-webkit-input-placeholder {
    color: #ffffff !important;
    opacity: 1 !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #89b4fa !important;
    box-shadow: none !important;
}

.stButton > button {
    background-color: #c0392b !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
}
.stButton > button:hover {
    background-color: #e74c3c !important;
    color: #ffffff !important;
}

h1, h2, h3, p, label, .stMarkdown { color: #cdd6f4 !important; }
</style>
""", unsafe_allow_html=True)

if not is_logged_in():
    render_login_page()
    st.stop()

user_id = get_current_user_id()
user_name = st.session_state.get("user_name", user_id)
run_startup_migrations()

with st.sidebar:
    st.title("🤖 Termai")
    st.caption(f"Signed in as **{user_name}** (`{user_id}`)")
    if st.button("Sign out", use_container_width=True):
        logout_session()
        st.rerun()
    st.divider()
    _pages = ["Agent", "Memory", "Skills"]
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = "Agent"
    page = st.radio(
        "Navigate",
        _pages,
        index=_pages.index(st.session_state.nav_page),
        key="sidebar_nav",
    )
    st.session_state.nav_page = page

# Fallback nav in main area (always visible if sidebar is collapsed)
_nav_cols = st.columns(3)
for i, name in enumerate(["Agent", "Memory", "Skills"]):
    with _nav_cols[i]:
        if st.button(name, key=f"nav_{name}", use_container_width=True):
            st.session_state.nav_page = name
            st.rerun()
page = st.session_state.nav_page

def _append_agent_event(event_type: str, content: str):
    if not content and event_type != "done":
        return
    safe = (content or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if event_type == "thinking":
        line = f'<div class="line-thinking">⠿ {safe}</div>'
    elif event_type == "skill":
        line = f'<div class="line-skill">📖 {safe}</div>'
    elif event_type == "tool":
        line = f'<div class="line-tool">🔧 {safe}</div>'
    elif event_type == "output":
        line = f'<div class="line-output">  {safe}</div>'
    elif event_type == "done":
        line = f'<div class="line-done">✅ {safe}</div>'
    elif event_type == "cost":
        line = (
            f'<div style="color:#6c6c6c;font-family:monospace;font-size:12px;margin:2px 0;">'
            f"🪙 {safe}</div>"
        )
    elif event_type == "error":
        line = f'<div class="line-error">✗ {safe}</div>'
    else:
        return
    st.session_state.log_lines.append(line)


def _drain_agent_queue():
    q = st.session_state.get("agent_queue")
    if not q:
        return
    while True:
        try:
            event_type, content = q.get_nowait()
        except queue.Empty:
            break
        if event_type == "__done__":
            st.session_state.agent_done = True
            continue
        _append_agent_event(event_type, content)


if page == "Agent":
    if "log_lines" not in st.session_state:
        st.session_state.log_lines = []
    if "running" not in st.session_state:
        st.session_state.running = False

    terminal_placeholder = st.empty()

    def render_terminal():
        inner = "\n".join(st.session_state.log_lines) if st.session_state.log_lines else \
            '<span style="color:#FFFFFF;font-family:monospace;">Termai is ready. Type a task below...</span>'
        terminal_placeholder.markdown(
            f'<div class="terminal-wrap">{inner}</div>',
            unsafe_allow_html=True,
        )

    def finish_agent_run():
        _drain_agent_queue()
        st.session_state.running = False
        st.session_state.pop("agent_thread", None)
        st.session_state.pop("agent_queue", None)
        st.session_state.pop("agent_done", None)
        st.session_state.pop("_poll_ts", None)
        from memory import sync_workspaces_to_memory

        sync_workspaces_to_memory(user_id)

    render_terminal()

    if st.session_state.running:
        _drain_agent_queue()
        render_terminal()
        thread = st.session_state.get("agent_thread")
        if thread and not thread.is_alive():
            finish_agent_run()
            render_terminal()
        else:
            now = time.time()
            if now - st.session_state.get("_poll_ts", 0) >= 0.4:
                st.session_state._poll_ts = now
                st.rerun()

    st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)

    st.markdown('<div class="input-wrap">', unsafe_allow_html=True)
    with st.form("task_form", clear_on_submit=False, border=False):
        col1, col2 = st.columns([11, 1])
        with col1:
            task = st.text_input(
                "task",
                label_visibility="collapsed",
                placeholder="$ Enter your task and press Enter...",
                disabled=st.session_state.running,
            )
        with col2:
            run_btn = st.form_submit_button(
                "▶ Run",
                type="primary",
                disabled=st.session_state.running,
                use_container_width=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

    if run_btn and (task or "").strip() and not st.session_state.running:
        safe_task = task.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        st.session_state.log_lines.append(f'<div class="line-task">$ {safe_task}</div>')
        st.session_state.running = True
        st.session_state.agent_done = False
        event_queue = queue.Queue()
        st.session_state.agent_queue = event_queue

        def callback(event_type: str, content: str):
            event_queue.put((event_type, content))

        run_user_id = user_id
        run_task = task.strip()

        def run():
            try:
                run_agent(run_task, user_id=run_user_id, callback=callback)
            except Exception as e:
                callback("error", str(e))
            finally:
                event_queue.put(("__done__", ""))

        thread = threading.Thread(target=run, daemon=True)
        st.session_state.agent_thread = thread
        thread.start()

elif page == "Memory":
    if st.session_state.get("running"):
        st.info("Agent is still running in the background. Open **Agent** to see live output.")
    st.title("Memory")
    st.caption(f"Storage: `memory/{user_id}.toon` · Workspaces: `workspaces/{user_id}/`")
    tasks = get_all_tasks(user_id)
    user_ws = user_workspace_root(user_id)
    try:
        task_dirs = [
            d for d in os.listdir(user_ws)
            if os.path.isdir(os.path.join(user_ws, d)) and not d.startswith(".")
        ]
        st.caption(f"{len(task_dirs)} workspace folder(s) on disk")
    except OSError:
        pass

    st.subheader("Task History")
    if not tasks:
        st.info("No tasks yet.")
    else:
        for t in reversed(tasks):
            with st.expander(f"[{t['timestamp']}] {t['task']}"):
                ws = t.get("workspace", "")
                if ws.startswith("(chat"):
                    st.caption("💬 Chat only — no workspace files")
                else:
                    st.caption(f"📂 {ws}")
                if t.get("summary"):
                    st.write(t["summary"])

elif page == "Skills":
    st.title("Skills")
    skills = list_skills()
    if not skills:
        st.info("No skills found in skills/ folder.")
    else:
        for s in skills:
            with st.expander(f"📖 {s['title']}  —  `{s['file']}`"):
                st.caption("Trigger keywords: " + ", ".join(s["keywords"]))
                skill_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "skills", s["file"]
                )
                with open(skill_path) as f:
                    st.markdown(f.read())
