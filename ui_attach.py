"""Paperclip attach control — native Streamlit uploader (reliable outside forms)."""

import streamlit as st

from uploads import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES


def attach_file_picker(*, disabled: bool = False) -> tuple[str, bytes] | None:
    """
    Blue paperclip opens a small popover with CSV/XLSX picker.
    Returns (filename, bytes) when a file is selected.
    """
    if disabled:
        st.button(
            "📎",
            disabled=True,
            use_container_width=True,
            help="Attach CSV or XLSX",
            key="agent_attach_btn_disabled",
        )
        return None

    with st.popover("📎", help="Attach CSV or XLSX", use_container_width=True):
        uploaded = st.file_uploader(
            "Choose CSV or XLSX",
            type=["csv", "xlsx"],
            label_visibility="collapsed",
            key="agent_attach_uploader",
        )

    if uploaded is None:
        return None

    name = uploaded.name
    data = uploaded.getvalue()
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_EXTENSIONS:
        return None
    if len(data) > MAX_UPLOAD_BYTES:
        return None
    return name, data
