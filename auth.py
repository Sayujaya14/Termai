"""Username/password and Google OAuth auth backed by users.json."""

import json
import os
import re
import sys

import bcrypt

from paths import GOOGLE_USER_ID_RE, USER_ID_RE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.getenv("TERMAI_USERS_FILE", os.path.join(BASE_DIR, "users.json"))
USERNAME_RE = USER_ID_RE


def _load_users_raw() -> dict:
    """Load users.json as a dict (empty if missing or invalid)."""
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _save_users_raw(data: dict) -> None:
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _valid_user_key(username: str) -> bool:
    return bool(USERNAME_RE.match(username) or GOOGLE_USER_ID_RE.match(username))


def load_all_users() -> dict[str, dict]:
    """All users from users.json (password and Google)."""
    users = {}
    for username, info in _load_users_raw().items():
        if not _valid_user_key(username) or not isinstance(info, dict):
            continue
        entry: dict = {"name": info.get("name", username)}
        if "password_hash" in info:
            entry["password_hash"] = info["password_hash"]
        if info.get("auth_provider") == "google":
            entry["auth_provider"] = "google"
            entry["google_sub"] = info.get("google_sub", "")
            entry["email"] = info.get("email", "")
        users[username] = entry
    return users


def load_users() -> dict[str, dict]:
    """Return validated password users: username -> {name, password_hash}."""
    users = {}
    for username, info in load_all_users().items():
        if not USERNAME_RE.match(username):
            continue
        if "password_hash" not in info:
            continue
        users[username] = {
            "name": info["name"],
            "password_hash": info["password_hash"],
        }
    return users


def register_or_update_google_user(
    user_id: str,
    name: str,
    email: str,
    google_sub: str,
) -> None:
    """Persist or refresh a Google-authenticated user in users.json."""
    data = _load_users_raw()
    existing = data.get(user_id, {})
    entry = dict(existing) if isinstance(existing, dict) else {}
    entry.update({
        "name": name,
        "auth_provider": "google",
        "google_sub": google_sub,
        "email": email,
    })
    data[user_id] = entry
    _save_users_raw(data)


def verify_password(username: str, password: str) -> bool:
    """Check plaintext password against stored bcrypt hash."""
    users = load_users()
    user = users.get(username)
    if not user:
        return False
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            user["password_hash"].encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def authenticate(username: str, password: str) -> dict | None:
    """On success return {user_id, name}; otherwise None."""
    username = username.strip().lower()
    if not USERNAME_RE.match(username):
        return None
    if not verify_password(username, password):
        return None
    user = load_users()[username]
    return {"user_id": username, "name": user["name"]}


def hash_password(password: str) -> str:
    """Generate bcrypt hash for users.json (CLI: python auth.py hash-password)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def users_file_ready() -> bool:
    """True if at least one valid password user exists in users.json."""
    return bool(load_users())


def auth_ready() -> bool:
    """True when password login or Google OAuth is available."""
    from google_auth import google_oauth_configured

    return users_file_ready() or google_oauth_configured()


# ── Streamlit session helpers ────────────────────────────────────────────────

def is_logged_in() -> bool:
    """True when Streamlit session has authenticated user_id."""
    import streamlit as st

    return bool(
        st.session_state.get("authenticated")
        and st.session_state.get("user_id")
    )


def get_current_user_id() -> str | None:
    """Logged-in username for the current Streamlit session."""
    import streamlit as st

    if is_logged_in():
        return st.session_state["user_id"]
    return None


def login_session(user_id: str, display_name: str | None = None) -> None:
    """Store auth state in st.session_state after successful login."""
    import streamlit as st

    from paths import validate_user_id

    user_id = validate_user_id(user_id)
    if display_name is None:
        all_users = load_all_users()
        display_name = all_users.get(user_id, {}).get("name", user_id)

    st.session_state.authenticated = True
    st.session_state.user_id = user_id
    st.session_state.user_name = display_name
    st.session_state.pop("log_lines", None)
    st.session_state.pop("running", None)


def logout_session() -> None:
    """Clear all Streamlit session state (sign out)."""
    import streamlit as st

    for key in list(st.session_state.keys()):
        del st.session_state[key]


def handle_google_oauth_callback() -> bool:
    """Complete Google OAuth if query params are present. Returns True on login."""
    import streamlit as st

    from google_auth import complete_google_oauth, google_oauth_configured

    if not google_oauth_configured():
        return False

    params = st.query_params
    code = params.get("code")
    state = params.get("state")
    if not code or not state:
        return False

    try:
        result = complete_google_oauth(code, state)
    except PermissionError as exc:
        st.error(str(exc))
        st.query_params.clear()
        return False

    st.query_params.clear()

    if not result:
        st.error("Google sign-in failed. Please try again.")
        return False

    register_or_update_google_user(
        result["user_id"],
        result["name"],
        result.get("email", ""),
        result["google_sub"],
    )
    login_session(result["user_id"], result["name"])
    return True


def render_login_page() -> None:
    """Render the sign-in page with Google OAuth and username/password."""
    import streamlit as st

    from google_auth import (
        build_google_auth_url,
        get_effective_redirect_uri,
        google_oauth_configured,
        streamlit_request_headers,
    )
    from ui_styles import inject_global_css, inject_login_page_css, render_google_signin_button

    inject_global_css()
    inject_login_page_css()

    if handle_google_oauth_callback():
        st.rerun()

    google_ready = google_oauth_configured()
    password_ready = users_file_ready()
    submitted = False
    username = ""
    password = ""

    st.markdown(
        """
        <div class="login-logo">Termai</div>
        <div class="login-tagline">AI coding agent with terminal access</div>
        """,
        unsafe_allow_html=True,
    )

    if google_ready:
        headers = streamlit_request_headers()
        redirect_uri = get_effective_redirect_uri(headers)
        try:
            auth_url = build_google_auth_url(redirect_uri)
            st.markdown(
                render_google_signin_button(href=auth_url),
                unsafe_allow_html=True,
            )
        except ValueError as exc:
            st.markdown(
                render_google_signin_button(disabled=True),
                unsafe_allow_html=True,
            )
            st.caption(str(exc))
    else:
        st.markdown(
            render_google_signin_button(disabled=True),
            unsafe_allow_html=True,
        )

    if password_ready:
        st.markdown(
            '<div class="login-divider"><span>or</span></div>',
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="alice")
            password = st.text_input(
                "Password", type="password", placeholder="••••••••"
            )
            submitted = st.form_submit_button(
                "Sign in", type="primary", use_container_width=True
            )
    elif not google_ready:
        st.error(
            "No sign-in method configured. Copy `users.json.example` to "
            "`users.json`, or set Google OAuth credentials in `.env`."
        )
        st.code("cp users.json.example users.json", language="bash")

    if submitted and password_ready:
        if not username.strip() or not password:
            st.warning("Enter username and password.")
        else:
            session = authenticate(username, password)
            if session:
                login_session(session["user_id"])
                st.rerun()
            else:
                st.error("Invalid username or password.")


# ── CLI ──────────────────────────────────────────────────────────────────────

def cli_resolve_user(args: list[str]) -> tuple[str | None, list[str]]:
    """Parse --user and --password from argv; returns (user_id, remaining_args)."""
    user_id = None
    password = os.getenv("TERMAI_PASSWORD", "")
    rest = []
    i = 0
    while i < len(args):
        if args[i] == "--user" and i + 1 < len(args):
            user_id = args[i + 1].strip().lower()
            i += 2
        elif args[i] == "--password" and i + 1 < len(args):
            password = args[i + 1]
            i += 2
        else:
            rest.append(args[i])
            i += 1
    if user_id and password:
        if authenticate(user_id, password):
            return user_id, rest
        print("Invalid username or password.", file=sys.stderr)
        sys.exit(1)
    if user_id:
        print("CLI requires --password or TERMAI_PASSWORD env var.", file=sys.stderr)
        sys.exit(1)
    return None, rest


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "hash-password":
        print("Usage: python auth.py hash-password <plain_password>")
        sys.exit(1)
    print(hash_password(sys.argv[2]))
