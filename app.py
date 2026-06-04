"""
Streamlit web UI for Termai.

Pages: Agent (terminal + run), Persona (bootstrap files), Memory, Skills.
Runs run_agent() in a background thread and polls events into the terminal view.
"""

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
from memory import (
    clear_conversation_memory,
    get_all_tasks,
    get_conversation_turn_count,
)
from paths import user_agent_home, user_workspace_root, is_task_workspace_dir
from persona import (
    ensure_persona_files,
    list_persona_files,
    read_persona_file,
    reset_persona_file,
    write_persona_file,
)
from skills import list_skills
from ui_attach import attach_file_picker
from ui_styles import inject_global_css, page_header
from workspace_zip import zip_workspace

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
_pages = ["Agent", "Persona", "Memory", "Skills"]
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
    """Convert agent callback events into HTML lines in session log_lines."""
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
    elif event_type == "file":
        line = f'<div class="line-file">File: {safe}</div>'
    else:
        return
    st.session_state.log_lines.append(line)


def _announce_uploaded_file(filename: str) -> None:
    """Show 'File: name.csv' once in the terminal when user attaches a dataset."""
    if st.session_state.get("announced_upload") == filename:
        return
    st.session_state.announced_upload = filename
    _append_agent_event("file", filename)


def _drain_agent_queue():
    """Pull all pending (event_type, content) tuples from the agent thread queue."""
    q = st.session_state.get("agent_queue")
    if not q:
        return
    while True:
        try:
            event_type, content = q.get_nowait()
        except queue.Empty:
            break
        if event_type == "__done__":
            continue
        if event_type == "workspace":
            st.session_state.task_workspace = content
            continue
        _append_agent_event(event_type, content)


def _terminal_inner_html() -> str:
    """Join log_lines into HTML for the terminal panel."""
    if st.session_state.get("log_lines"):
        return "\n".join(st.session_state.log_lines)
    return (
        '<div class="terminal-empty">'
        "<span>$</span> Ready — describe a task below and press "
        "<span>Run</span> or Enter."
        "</div>"
    )


def _render_terminal():
    """Update the terminal placeholder with current log HTML."""
    ph = st.session_state.get("terminal_ph")
    if ph is None:
        return
    ph.markdown(
        f'<div class="terminal-wrap">{_terminal_inner_html()}</div>',
        unsafe_allow_html=True,
    )


def _agent_thread_finished() -> bool:
    """True when the background run_agent thread has exited."""
    thread = st.session_state.get("agent_thread")
    return thread is None or not thread.is_alive()


def _prepare_task_download():
    """Build zip of last task workspace for st.download_button."""
    ws = st.session_state.pop("task_workspace", None)
    st.session_state.pop("task_zip", None)
    st.session_state.pop("task_zip_name", None)
    if not ws or ws.startswith("(chat") or not os.path.isdir(ws):
        return
    packed = zip_workspace(ws)
    if packed:
        data, filename = packed
        st.session_state.task_zip = data
        st.session_state.task_zip_name = filename
        st.session_state.log_lines.append(
            f'<div class="line-thinking">📦 Outputs zipped — use Download below '
            f"({html.escape(filename)})</div>"
        )


def _finish_agent_run():
    """Clear running state, zip outputs, sync memory after agent thread ends."""
    _drain_agent_queue()
    _prepare_task_download()
    st.session_state.running = False
    st.session_state.pop("agent_thread", None)
    st.session_state.pop("agent_queue", None)
    st.session_state.pop("announced_upload", None)
    st.session_state.pop("pending_upload", None)
    st.session_state.pop("agent_attach_uploader", None)
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
    """Render Memory page task cards from get_all_tasks() rows."""
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
        st.session_state.log_lines = [
        """
<div style="
    color:#00ff88;
    font-family:'JetBrains Mono',monospace;
    padding:12px 0;
    line-height:1.25;
    white-space:pre;
    text-shadow:0 0 8px rgba(0,255,136,0.35);
    overflow-x:auto;
">

╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║ ████████╗███████╗██████╗ ███╗   ███╗ █████╗ ██╗              ║
║ ╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██╔══██╗██║              ║
║    ██║   █████╗  ██████╔╝██╔████╔██║███████║██║              ║
║    ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██╔══██║██║              ║
║    ██║   ███████╗██║  ██║██║ ╚═╝ ██║██║  ██║██║              ║
║    ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝              ║
║                                                              ║
║                 Welcome to TermAI                            ║
║              AI Terminal Coding Agent                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

</div>
        """,

        """
<div style="
    color:#6c6c6c;
    font-family:'JetBrains Mono',monospace;
    font-size:13px;
    margin-top:8px;
    line-height:1.5;
">

$ System initialized<br>
$ OpenRouter fallback ready<br>
$ Workspace manager online<br>
$ Memory engine connected<br>
$ Awaiting task input...

</div>
        """
    ]
    if "running" not in st.session_state:
        st.session_state.running = False
    if "pending_upload" not in st.session_state:
        st.session_state.pending_upload = None
    if "announced_upload" not in st.session_state:
        st.session_state.announced_upload = None

    # Fragment updates session state but not the form — finish + rerun here too
    if st.session_state.running:
        _drain_agent_queue()
    _maybe_finish_agent_run(rerun_after=True)

    st.session_state.terminal_ph = st.empty()
    poll_agent_terminal()

    if (
        not st.session_state.running
        and st.session_state.get("task_zip")
        and st.session_state.get("task_zip_name")
    ):
        st.download_button(
            label=f"Download outputs ({st.session_state.task_zip_name})",
            data=st.session_state.task_zip,
            file_name=st.session_state.task_zip_name,
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )

    st.markdown("<div style='height:88px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="input-bar">', unsafe_allow_html=True)
    col_task, col_attach, col_run = st.columns([10, 1, 1], vertical_alignment="bottom")
    with col_attach:
        picked = attach_file_picker(disabled=st.session_state.running)
        if picked is not None:
            st.session_state.pending_upload = picked
            _announce_uploaded_file(picked[0])
    with col_task:
        task = st.text_input(
            "task",
            label_visibility="collapsed",
            placeholder="Describe your task… (e.g. do an EDA on the uploaded file)",
            disabled=st.session_state.running,
            key="agent_task_input",
        )
    with col_run:
        run_btn = st.button(
            "Run",
            type="primary",
            disabled=st.session_state.running,
            use_container_width=True,
            key="agent_run_btn",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    task_text = (task or "").strip()
    run_upload = st.session_state.get("pending_upload")

    if run_btn and not st.session_state.running and (task_text or run_upload):
        if not task_text:
            task_text = "Analyze the uploaded data file."
        safe_task = task_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        st.session_state.log_lines.append(f'<div class="line-task">$ {safe_task}</div>')
        st.session_state.pop("task_zip", None)
        st.session_state.pop("task_zip_name", None)
        st.session_state.pop("task_workspace", None)
        st.session_state.running = True
        event_queue = queue.Queue()
        st.session_state.agent_queue = event_queue

        def callback(event_type: str, content: str):
            event_queue.put((event_type, content))

        run_user_id = user_id
        run_task = task_text
        captured_upload = run_upload

        def run():
            try:
                run_agent(
                    run_task,
                    user_id=run_user_id,
                    callback=callback,
                    upload=captured_upload,
                )
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

    chat_turns = get_conversation_turn_count(user_id)

    if st.button(
        "Clear conversation memory",
        help="Removes ChatGPT-style message history between runs. Task list and workspaces stay.",
        type="secondary",
    ):
        clear_conversation_memory(user_id)
        st.success("Conversation memory cleared.")
        st.rerun()

    tasks = get_all_tasks(user_id)
    user_ws = user_workspace_root(user_id)
    try:
        folder_count = len([
            d for d in os.listdir(user_ws)
            if os.path.isdir(os.path.join(user_ws, d)) and is_task_workspace_dir(d)
        ])
    except OSError:
        folder_count = 0

    st.markdown(
        f"""
        <div class="stat-row">
            <div class="stat-pill"><strong>{len(tasks)}</strong> tasks in memory</div>
            <div class="stat-pill"><strong>{chat_turns}</strong> conversation turns</div>
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

elif page == "Persona":
    st.session_state.pop("terminal_ph", None)
    page_header(
        "Persona",
        "OpenClaw-style bootstrap files — injected into every agent session.",
    )

    ensure_persona_files(user_id, user_name)
    agent_home = user_agent_home(user_id)
    persona_files = list_persona_files(user_id)

    st.markdown(
        f"""
        <div class="stat-row">
            <div class="stat-pill"><strong>{len(persona_files)}</strong> bootstrap files</div>
            <div class="stat-pill"><code>{html.escape(agent_home)}</code></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    file_labels = {
        row["file"]: f"{row['file']} — {row['description']}"
        for row in persona_files
    }
    if "persona_selected_file" not in st.session_state:
        st.session_state.persona_selected_file = "AGENTS.md"

    selected = st.selectbox(
        "Bootstrap file",
        options=list(file_labels.keys()),
        format_func=lambda f: file_labels[f],
        key="persona_file_select",
    )

    st.caption(f"Path: `{os.path.join(agent_home, selected)}`")
    current = read_persona_file(user_id, selected) or ""
    edited = st.text_area(
        "Content",
        value=current,
        height=420,
        key=f"persona_editor_{selected}",
        label_visibility="collapsed",
    )

    col_save, col_reset, _col_hint = st.columns([1, 1, 2])
    with col_save:
        if st.button("Save", type="primary", use_container_width=True):
            write_persona_file(user_id, selected, edited)
            st.success(f"Saved {selected}")
    with col_reset:
        if st.button("Reset to template", use_container_width=True):
            reset_persona_file(user_id, selected, user_name)
            st.rerun()
    with _col_hint:
        st.caption(
            "AGENTS.md · SOUL.md · USER.md · IDENTITY.md · TOOLS.md load every session. "
            "Optional: BOOTSTRAP.md (first run), MEMORY.md, memory/YYYY-MM-DD.md."
        )

    st.divider()
    cards = []
    for row in persona_files:
        status = "✓" if row["exists"] else "—"
        kind = "core" if row["core"] else "optional"
        cards.append(
            f'<div class="skill-card">'
            f'<h3>{html.escape(row["file"])} {status}</h3>'
            f'<p class="skill-kw">{html.escape(row["description"])}<br>'
            f'<span style="color:#6c9eff">{kind}</span></p></div>'
        )
    st.markdown(f'<div class="skill-grid">{"".join(cards)}</div>', unsafe_allow_html=True)

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
