import streamlit as st
import threading
import queue
import os
from memory import get_all_tasks
from skills import list_skills
from agent import run_agent

st.set_page_config(page_title="Termai", page_icon="🤖", layout="wide")

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem !important; padding-bottom: 0 !important; }

/* black background everywhere */
.stApp { background-color: #000000 !important; }
[data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #222; }
[data-testid="stSidebar"] * { color: #cdd6f4 !important; }

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

/* stick input to bottom */
.input-wrap {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #000000;
    border-top: 1px solid #222;
    padding: 12px 24px;
    z-index: 999;
}

/* keep input box itself with slight contrast */
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

/* red buttons */
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

/* page titles and text */
h1, h2, h3, p, label, .stMarkdown { color: #cdd6f4 !important; }
</style>
""", unsafe_allow_html=True)

# sidebar
with st.sidebar:
    st.title("🤖 Termai")
    st.caption("AI Terminal Agent")
    st.divider()
    page = st.radio("Navigate", ["Agent", "Memory", "Skills"], label_visibility="collapsed")


# ── Agent Page ───────────────────────────────────────────────────────────────
if page == "Agent":

    if "log_lines" not in st.session_state:
        st.session_state.log_lines = []
    if "running" not in st.session_state:
        st.session_state.running = False

    # ── OUTPUT AREA (top) ──
    terminal_placeholder = st.empty()

    def render():
        inner = "\n".join(st.session_state.log_lines) if st.session_state.log_lines else \
            '<span style="color:#FFFFFF;font-family:monospace;">Termai is ready. Type a task below...</span>'
        terminal_placeholder.markdown(
            f'<div class="terminal-wrap">{inner}</div>',
            unsafe_allow_html=True
        )

    render()

    # spacer so content isn't hidden behind fixed input bar
    st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)

    # ── INPUT BAR (bottom, fixed) ──
    st.markdown('<div class="input-wrap">', unsafe_allow_html=True)
    with st.form("task_form", clear_on_submit=False, border=False):
        col1, col2 = st.columns([11, 1])
        with col1:
            task = st.text_input(
                "task", label_visibility="collapsed",
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
    st.markdown('</div>', unsafe_allow_html=True)

    # ── RUN AGENT ──
    if run_btn and (task or "").strip() and not st.session_state.running:
        st.session_state.running = True
        safe_task = task.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        st.session_state.log_lines.append(f'<div class="line-task">$ {safe_task}</div>')
        render()

        q = queue.Queue()

        def callback(event_type: str, content: str):
            q.put((event_type, content))

        def run():
            run_agent(task.strip(), callback=callback)
            q.put(("__done__", ""))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        while True:
            try:
                event_type, content = q.get(timeout=120)
            except queue.Empty:
                break

            if event_type == "__done__":
                break

            safe = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            if event_type == "thinking":
                st.session_state.log_lines.append(f'<div class="line-thinking">⠿ {safe}</div>')
            elif event_type == "skill":
                st.session_state.log_lines.append(f'<div class="line-skill">📖 {safe}</div>')
            elif event_type == "tool":
                st.session_state.log_lines.append(f'<div class="line-tool">🔧 {safe}</div>')
            elif event_type == "output":
                st.session_state.log_lines.append(f'<div class="line-output">  {safe}</div>')
            elif event_type == "done":
                st.session_state.log_lines.append(f'<div class="line-done">✅ {safe}</div>')
            elif event_type == "cost":
                st.session_state.log_lines.append(f'<div style="color:#6c6c6c;font-family:monospace;font-size:12px;margin:2px 0;">🪙 {safe}</div>')
            elif event_type == "error":
                st.session_state.log_lines.append(f'<div class="line-error">✗ {safe}</div>')

            render()

        thread.join()
        st.session_state.running = False
        st.rerun()


# ── Memory Page ──────────────────────────────────────────────────────────────
elif page == "Memory":
    st.title("Memory")
    tasks = get_all_tasks()

    st.subheader("Task History")
    if not tasks:
        st.info("No tasks yet.")
    else:
        for t in reversed(tasks):
            with st.expander(f"[{t['timestamp']}] {t['task']}"):
                st.caption(f"📂 {t['workspace']}")
                if t.get("summary"):
                    st.write(t["summary"])


# ── Skills Page ───────────────────────────────────────────────────────────────
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
