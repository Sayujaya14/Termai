"""Shared Streamlit UI theme and helpers."""

import html


def inject_global_css() -> None:
    """Inject dark theme CSS (sidebar, terminal, forms, login, cards)."""
    import streamlit as st

    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg: #0a0a0f;
    --surface: #12121a;
    --surface-2: #1a1a24;
    --border: #2a2a3a;
    --text: #e8eaf0;
    --muted: #8b8fa8;
    --accent: #6c9eff;
    --accent-hover: #8ab4ff;
    --green: #7ee787;
    --yellow: #f9e2af;
    --purple: #c4a7ff;
    --red: #f38ba8;
    --radius: 10px;
}

#MainMenu, footer { visibility: hidden; height: 0 !important; }
header[data-testid="stHeader"] {
    visibility: visible !important;
    background: var(--bg) !important;
    border-bottom: 1px solid var(--border);
}
[data-testid="stSidebarCollapsedControl"],
button[data-testid="stExpandSidebarButton"] {
    color: var(--text) !important;
    background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

.stApp {
    background: var(--bg) !important;
    font-family: 'Inter', sans-serif !important;
}
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 1200px !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0e0e14 0%, #0a0a0f 100%) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.25rem !important;
}
.brand-title {
    font-family: 'Inter', sans-serif;
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text);
    margin: 0 0 0.15rem 0;
    letter-spacing: -0.02em;
}
.brand-sub {
    font-size: 0.8rem;
    color: var(--muted);
    margin-bottom: 1rem;
}
.user-chip {
    display: inline-block;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 6px 12px;
    font-size: 0.78rem;
    color: var(--muted);
    margin-bottom: 1rem;
}
.user-chip strong { color: var(--accent); }

/* Sidebar nav radios → menu buttons */
[data-testid="stSidebar"] [role="radiogroup"] {
    gap: 6px !important;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 0.65rem 1rem !important;
    margin: 0 !important;
    color: var(--text) !important;
    font-weight: 500 !important;
    transition: all 0.15s ease;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    border-color: var(--accent) !important;
    background: var(--surface-2) !important;
}
[data-testid="stSidebar"] [role="radiogroup"] label[data-testid="stRadioButton"] {
    /* streamlit version variance */
}
div[data-testid="stSidebar"] label:has(div[aria-checked="true"]) {
    background: rgba(108, 158, 255, 0.15) !important;
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}
[data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {
    display: none !important;
}

/* Page header */
.page-header {
    margin-bottom: 1.25rem;
}
.page-header h1 {
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    color: var(--text) !important;
    margin: 0 0 0.35rem 0 !important;
    letter-spacing: -0.03em;
}
.page-header p {
    color: var(--muted) !important;
    font-size: 0.9rem !important;
    margin: 0 !important;
}

/* Stat pills */
.stat-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 1.25rem;
}
.stat-pill {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 14px;
    font-size: 0.8rem;
    color: var(--muted);
}
.stat-pill strong {
    color: var(--text);
    display: block;
    font-size: 1.1rem;
    margin-bottom: 2px;
}

/* Task cards */
.task-grid { display: flex; flex-direction: column; gap: 10px; }
.task-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 16px;
    transition: border-color 0.15s;
}
.task-card:hover { border-color: var(--accent); }
.task-card-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 8px;
}
.task-card-title {
    color: var(--text);
    font-weight: 600;
    font-size: 0.95rem;
    margin: 0;
}
.task-card-time {
    color: var(--muted);
    font-size: 0.75rem;
    white-space: nowrap;
}
.task-card-meta {
    color: var(--muted);
    font-size: 0.78rem;
    font-family: 'JetBrains Mono', monospace;
    word-break: break-all;
}
.task-card-summary {
    color: #b8bcc8;
    font-size: 0.85rem;
    line-height: 1.45;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid var(--border);
}
.badge-chat {
    display: inline-block;
    background: rgba(196, 167, 255, 0.15);
    color: var(--purple);
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 999px;
    margin-bottom: 6px;
}

/* Skill cards */
.skill-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
}
.skill-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
}
.skill-card h3 {
    color: var(--text) !important;
    font-size: 1rem !important;
    margin: 0 0 8px 0 !important;
}
.skill-kw {
    color: var(--muted);
    font-size: 0.78rem;
    line-height: 1.4;
}

/* Terminal */
.line-tool     { color: var(--accent); margin: 2px 0; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.line-output   { color: var(--green); margin: 1px 0; font-family: 'JetBrains Mono', monospace; font-size: 13px; padding-left: 16px; }
.line-done     { color: var(--green); font-weight: 600; margin: 6px 0 2px 0; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.line-skill    { color: var(--yellow); margin: 2px 0; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.line-thinking { color: var(--purple); margin: 2px 0; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.line-task     { color: var(--text); font-weight: 600; margin: 8px 0 6px 0; font-family: 'JetBrains Mono', monospace; font-size: 14px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
.line-file     { color: var(--accent); margin: 4px 0 6px 0; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.line-error    { color: var(--red); margin: 2px 0; font-family: 'JetBrains Mono', monospace; font-size: 13px; }

.terminal-wrap {
    background: #08080c;
    border-radius: 12px;
    border: 1px solid var(--border);
    padding: 18px;
    min-height: 68vh;
    max-height: 68vh;
    overflow-y: auto;
    box-shadow: inset 0 2px 24px rgba(0,0,0,0.4);
}
.terminal-empty {
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
}
.terminal-empty span { color: var(--accent); }

.input-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: linear-gradient(0deg, var(--bg) 70%, transparent);
    border-top: 1px solid var(--border);
    padding: 14px 24px 18px;
    z-index: 99;
}

/* Paperclip attach column (popover button) — first column in input bar */
.input-bar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-of-type(1) {
    flex: 0 0 52px !important;
    min-width: 52px !important;
    max-width: 52px !important;
}
.input-bar [data-testid="stColumn"]:nth-of-type(1) [data-testid="stPopoverButton"] > button,
.input-bar [data-testid="stColumn"]:nth-of-type(1) > div > button {
    width: 44px !important;
    height: 44px !important;
    min-width: 44px !important;
    padding: 0 !important;
    font-size: 1.1rem !important;
    line-height: 1 !important;
    background: var(--accent) !important;
    color: #0a0a0f !important;
    border: none !important;
    border-radius: var(--radius) !important;
}
.input-bar [data-testid="stColumn"]:nth-of-type(1) [data-testid="stPopoverButton"] > button:hover {
    background: var(--accent-hover) !important;
    color: #0a0a0f !important;
}
/* Popover panel: hide 200MB limit text */
[data-testid="stPopoverBody"] [data-testid="stFileUploader"] small,
[data-testid="stPopoverBody"] [data-testid="stCaptionContainer"] {
    display: none !important;
}

.input-bar [data-testid="stForm"] {
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
}
.input-bar [data-testid="stFormSubmitButton"] > button {
    min-height: 44px !important;
}

/* Inputs & buttons */
div[data-testid="stTextInput"] input,
div[data-testid="stTextInput"] input:focus {
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 14px !important;
    box-shadow: none !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
}
div[data-testid="stTextInput"] input::placeholder {
    color: var(--muted) !important;
    opacity: 1 !important;
}
div[data-testid="stTextInput"] input:disabled {
    background: var(--surface-2) !important;
    color: var(--muted) !important;
    -webkit-text-fill-color: var(--muted) !important;
    opacity: 1 !important;
}

/* Selectbox */
div[data-testid="stSelectbox"] label,
div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] p {
    color: var(--text) !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background-color: var(--surface) !important;
    border-color: var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text) !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] input {
    background-color: transparent !important;
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] span,
div[data-testid="stSelectbox"] [data-baseweb="select"] div {
    color: var(--text) !important;
    background-color: transparent !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] svg {
    fill: var(--muted) !important;
    color: var(--muted) !important;
}
div[data-baseweb="popover"] ul[data-baseweb="menu"],
div[data-baseweb="popover"] [role="listbox"] {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
}
div[data-baseweb="popover"] li[role="option"],
div[data-baseweb="popover"] li[data-baseweb="option"] {
    color: var(--text) !important;
    background-color: var(--surface) !important;
}
div[data-baseweb="popover"] li[role="option"]:hover,
div[data-baseweb="popover"] li[data-baseweb="option"]:hover {
    background-color: var(--surface-2) !important;
}
div[data-baseweb="popover"] li[aria-selected="true"] {
    background-color: rgba(108, 158, 255, 0.18) !important;
    color: var(--accent) !important;
}

/* Number input */
div[data-testid="stNumberInput"] label,
div[data-testid="stNumberInput"] [data-testid="stWidgetLabel"] p {
    color: var(--text) !important;
}
div[data-testid="stNumberInput"] [data-baseweb="input"] {
    background: transparent !important;
}
div[data-testid="stNumberInput"] [data-baseweb="input"] > div {
    background: var(--surface) !important;
    border-color: var(--border) !important;
    border-radius: var(--radius) !important;
}
div[data-testid="stNumberInput"] input {
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    font-family: 'JetBrains Mono', monospace !important;
    box-shadow: none !important;
    -webkit-text-fill-color: var(--text) !important;
}
div[data-testid="stNumberInput"] input:focus {
    border-color: var(--accent) !important;
}
div[data-testid="stNumberInput"] button {
    background: var(--surface-2) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
}
div[data-testid="stNumberInput"] button:hover {
    background: var(--surface) !important;
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}
div[data-testid="stNumberInput"] button svg {
    fill: currentColor !important;
    stroke: currentColor !important;
}

/* Textarea (Persona editor) */
div[data-testid="stTextArea"] textarea,
div[data-testid="stTextArea"] textarea:focus {
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    font-family: 'JetBrains Mono', monospace !important;
    box-shadow: none !important;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color: var(--accent) !important;
}

/* Form labels & help icons */
[data-testid="stForm"] label p,
[data-testid="stForm"] [data-testid="stWidgetLabel"] p {
    color: var(--text) !important;
}
[data-testid="stForm"] [data-testid="stTooltipIcon"] {
    color: var(--muted) !important;
}

.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"],
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"],
.stFormSubmitButton > button {
    background: var(--accent) !important;
    color: #0a0a0f !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: var(--radius) !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover,
div[data-testid="stButton"] > button[kind="primary"]:hover,
div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover,
.stFormSubmitButton > button:hover {
    background: var(--accent-hover) !important;
    color: #0a0a0f !important;
}
.stButton > button[kind="secondary"],
.stButton > button[data-testid="stBaseButton-secondary"],
div[data-testid="stButton"] > button[kind="secondary"],
div[data-testid="stButton"] > button[data-testid="stBaseButton-secondary"] {
    background: var(--surface-2) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
}
.stButton > button[kind="secondary"]:hover,
.stButton > button[data-testid="stBaseButton-secondary"]:hover,
div[data-testid="stButton"] > button[kind="secondary"]:hover,
div[data-testid="stButton"] > button[data-testid="stBaseButton-secondary"]:hover {
    background: var(--surface) !important;
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

/* Tooltips (button help, widget help icons) */
div[data-baseweb="tooltip"],
div[data-baseweb="tooltip"] > div,
[role="tooltip"],
[data-testid="stTooltipContent"] {
    background-color: var(--surface-2) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.55) !important;
    z-index: 99999 !important;
}
div[data-baseweb="tooltip"] div,
div[data-baseweb="tooltip"] p,
div[data-baseweb="tooltip"] span,
div[data-baseweb="tooltip"] li,
[role="tooltip"] div,
[role="tooltip"] p,
[role="tooltip"] span,
[data-testid="stTooltipContent"] div,
[data-testid="stTooltipContent"] p,
[data-testid="stTooltipContent"] span {
    color: var(--text) !important;
    background-color: transparent !important;
}
div[data-baseweb="tooltip"] a {
    color: var(--accent) !important;
}
div[data-baseweb="tooltip"] svg {
    fill: var(--surface-2) !important;
    background: transparent !important;
}

/* Alerts */
[data-testid="stAlert"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text) !important;
}

/* Login */
.login-wrap {
    max-width: 400px;
    margin: 4rem auto 2rem;
    padding: 2rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.35);
}
.login-logo {
    font-size: 2rem;
    font-weight: 700;
    color: var(--text);
    text-align: center;
    margin-bottom: 0.25rem;
}
.login-tagline {
    text-align: center;
    color: var(--muted);
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
}

h1, h2, h3, p, label, .stMarkdown { color: var(--text); }
</style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "") -> None:
    """Styled page title + optional subtitle for Agent, Memory, Persona, Skills."""
    import streamlit as st

    sub = f"<p>{html.escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f'<div class="page-header"><h1>{html.escape(title)}</h1>{sub}</div>',
        unsafe_allow_html=True,
    )
