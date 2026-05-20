import html
import os
import queue
import threading
from datetime import timedelta

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
from ui_styles import inject_global_css, page_header

st.set_page_config(
    page_title="Termai",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()

if not is_logged_in():
    render_login_page()
    st.stop()

user_id = get_current_user_id()
user_name = st.session_state.get("user_name", user_id)
run_startup_migrations()

_pages = ["Agent", "Memory", "Skills"]
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Agent"

with st.sidebar:
    st.markdown(
        '<p class="brand-title">Termai</p><p class="brand-sub">AI terminal agent</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<span class="user-chip">Signed in as <strong>{html.escape(user_name)}</strong> '
        f'({html.escape(user_id)})</span>',
        unsafe_allow_html=True,
    )
    page = st.radio(
        "Menu",
        _pages,
        index=_pages.index(st.session_state.nav_page),
        key="sidebar_nav",
        label_visibility="collapsed",
    )
    st.session_state.nav_page = page
    st.divider()
    if st.button("Sign out", use_container_width=True, type="secondary"):
        logout_session()
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
            f'<div style="color:#6c6c6c;font-family:JetBrains Mono,monospace;'
            f'font-size:12px;margin:2px 0;">🪙 {safe}</div>'
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


def _terminal_inner_html() -> str:
    if st.session_state.get("log_lines"):
        return "\n".join(st.session_state.log_lines)
    return (
        '<div class="terminal-empty">'
        "<span>$</span> Ready — describe a task below and press "
        "<span>Run</span> or Enter."
        "</div>"
    )


def _render_terminal():
    ph = st.session_state.get("terminal_ph")
    if ph is None:
        return
    ph.markdown(
        f'<div class="terminal-wrap">{_terminal_inner_html()}</div>',
        unsafe_allow_html=True,
    )


def _agent_thread_finished() -> bool:
    thread = st.session_state.get("agent_thread")
    return thread is None or not thread.is_alive()


def _finish_agent_run():
    _drain_agent_queue()
    st.session_state.running = False
    st.session_state.pop("agent_thread", None)
    st.session_state.pop("agent_queue", None)
    st.session_state.pop("agent_done", None)
    from memory import sync_workspaces_to_memory

    uid = get_current_user_id()
    if uid:
        sync_workspaces_to_memory(uid)


def _maybe_finish_agent_run(*, rerun_after: bool = False) -> bool:
    """Return True if the run was finished (clears running lock)."""
    if not st.session_state.get("running"):
        return False
    if not _agent_thread_finished():
        return False
    _finish_agent_run()
    if rerun_after:
        st.rerun()
    return True


@st.fragment(run_every=timedelta(seconds=0.35))
def poll_agent_terminal():
    """Refresh terminal while agent runs; only active on Agent page."""
    if st.session_state.get("nav_page") != "Agent":
        return
    if st.session_state.get("terminal_ph") is None:
        return

    if st.session_state.get("running"):
        _drain_agent_queue()

    _render_terminal()

    if _maybe_finish_agent_run(rerun_after=True):
        return


def _render_task_cards(tasks: list) -> None:
    cards = []
    for t in reversed(tasks):
        ws = t.get("workspace", "")
        title = html.escape(t.get("task", ""))
        ts = html.escape(t.get("timestamp", ""))
        summary = html.escape((t.get("summary") or "")[:300])
        if ws.startswith("(chat"):
            meta = '<span class="badge-chat">Chat only</span>'
        else:
            meta = f'<div class="task-card-meta">📂 {html.escape(ws)}</div>'
        summary_block = (
            f'<div class="task-card-summary">{summary}</div>' if summary else ""
        )
        cards.append(
            f'<div class="task-card">'
            f'<div class="task-card-head">'
            f'<p class="task-card-title">{title}</p>'
            f'<span class="task-card-time">{ts}</span></div>'
            f"{meta}{summary_block}</div>"
        )
    st.markdown(
        f'<div class="task-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


if page == "Agent":
    page_header("Agent", "Run tasks — code, shell, and files in your private workspace.")

    if "log_lines" not in st.session_state:
        st.session_state.log_lines = []
    if "running" not in st.session_state:
        st.session_state.running = False

    # Fragment updates session state but not the form — finish + rerun here too
    if st.session_state.running:
        _drain_agent_queue()
    _maybe_finish_agent_run(rerun_after=True)

    st.session_state.terminal_ph = st.empty()
    poll_agent_terminal()

    st.markdown("<div style='height:88px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="input-bar">', unsafe_allow_html=True)
    with st.form("task_form", clear_on_submit=False, border=False):
        col1, col2 = st.columns([11, 1])
        with col1:
            task = st.text_input(
                "task",
                label_visibility="collapsed",
                placeholder="Describe your task…",
                disabled=st.session_state.running,
            )
        with col2:
            run_btn = st.form_submit_button(
                "Run",
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
        st.rerun()

elif page == "Memory":
    st.session_state.pop("terminal_ph", None)
    if st.session_state.get("running"):
        st.info("Agent is still running. Open **Agent** from the sidebar for live output.")

    page_header(
        "Memory",
        f"Your task history and workspaces · memory/{user_id}.toon",
    )

    tasks = get_all_tasks(user_id)
    user_ws = user_workspace_root(user_id)
    try:
        folder_count = len([
            d for d in os.listdir(user_ws)
            if os.path.isdir(os.path.join(user_ws, d)) and not d.startswith(".")
        ])
    except OSError:
        folder_count = 0

    st.markdown(
        f"""
        <div class="stat-row">
            <div class="stat-pill"><strong>{len(tasks)}</strong> tasks in memory</div>
            <div class="stat-pill"><strong>{folder_count}</strong> workspace folders</div>
            <div class="stat-pill"><strong>{user_id}</strong> user scope</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not tasks:
        st.markdown(
            """
            <div class="task-card" style="text-align:center;padding:2rem;">
                <p style="color:#8b8fa8;margin:0;">No tasks yet.</p>
                <p style="color:#6c9eff;margin:0.5rem 0 0;font-size:0.85rem;">
                    Run something on the Agent page to build history.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        _render_task_cards(tasks)

elif page == "Skills":
    st.session_state.pop("terminal_ph", None)
    page_header("Skills", "Guides the agent loads when your task matches trigger keywords.")

    skills = list_skills()
    if not skills:
        st.info("No skills in the `skills/` folder yet.")
    else:
        cards = []
        for s in skills:
            kws = ", ".join(html.escape(k) for k in s["keywords"][:6])
            cards.append(
                f'<div class="skill-card">'
                f'<h3>{html.escape(s["title"])}</h3>'
                f'<p class="skill-kw"><code>{html.escape(s["file"])}</code><br>'
                f"Triggers: {kws}</p></div>"
            )
        st.markdown(f'<div class="skill-grid">{"".join(cards)}</div>', unsafe_allow_html=True)

        st.divider()
        st.caption("Full skill documents")
        for s in skills:
            with st.expander(s["title"]):
                skill_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "skills", s["file"]
                )
                with open(skill_path) as f:
                    st.markdown(f.read())
