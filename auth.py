"""Username/password auth backed by users.json (bcrypt hashes)."""

import json
import os
import re
import sys

import bcrypt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.getenv("TERMAI_USERS_FILE", os.path.join(BASE_DIR, "users.json"))
USERNAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")


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


def load_users() -> dict[str, dict]:
    """Return validated users: username -> {name, password_hash}."""
    users = {}
    for username, info in _load_users_raw().items():
        if not USERNAME_RE.match(username):
            continue
        if not isinstance(info, dict) or "password_hash" not in info:
            continue
        users[username] = {
            "name": info.get("name", username),
            "password_hash": info["password_hash"],
        }
    return users


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
    """True if at least one valid user exists in users.json."""
    return bool(load_users())


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


def login_session(username: str) -> None:
    """Store auth state in st.session_state after successful login."""
    import streamlit as st

    user = load_users()[username]
    st.session_state.authenticated = True
    st.session_state.user_id = username
    st.session_state.user_name = user["name"]
    st.session_state.pop("log_lines", None)
    st.session_state.pop("running", None)


def logout_session() -> None:
    """Clear all Streamlit session state (sign out)."""
    import streamlit as st

    for key in list(st.session_state.keys()):
        del st.session_state[key]


def render_login_page() -> None:
    """Render the sign-in form when the user is not authenticated."""
    import streamlit as st

    from ui_styles import inject_global_css

    inject_global_css()

    st.markdown(
        """
        <div class="login-wrap">
            <div class="login-logo">Termai</div>
            <div class="login-tagline">AI coding agent with terminal access</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not users_file_ready():
        st.error(
            "No users configured. Copy `users.json.example` to `users.json`."
        )
        st.code("cp users.json.example users.json", language="bash")
        return

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="alice")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button(
                "Sign in", type="primary", use_container_width=True
            )

    if submitted:
        if not username.strip() or not password:
            st.warning("Enter username and password.")
            return
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
