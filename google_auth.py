"""
Google OAuth 2.0 sign-in for the Termai Streamlit web UI.

Flow:
  1. User clicks "Continue with Google" → build_google_auth_url() sends them to Google.
  2. Google redirects back to GOOGLE_REDIRECT_URI with ?code=...&state=...
  3. auth.handle_google_oauth_callback() calls complete_google_oauth() to finish login.

Why ngrok support exists (optional — not needed for normal localhost use):
  Google OAuth requires the redirect URI to match exactly what is registered in
  Google Cloud Console. When you expose your local Streamlit app through an ngrok
  tunnel (e.g. https://abc123.ngrok-free.app), Google must redirect to that public
  URL — not http://localhost:8501 — because the user's browser cannot reach your
  localhost. The ngrok helpers pick the correct public redirect URI when
  TERMAI_NGROK_URL is set or when the request comes through an ngrok host.
  For everyday local dev, set GOOGLE_REDIRECT_URI=http://localhost:8501 and ignore ngrok.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request

from config import (
    GOOGLE_ALLOWED_DOMAINS,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    NGROK_PUBLIC_URL,
    OAUTH_DYNAMIC_REDIRECT,
    OAUTH_STATE_SECRET,
)

# Google OAuth endpoints (standard OAuth 2.0 / OpenID Connect).
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# Hostnames allowed as redirect targets when TERMAI_OAUTH_DYNAMIC_REDIRECT=true.
# Prevents accepting arbitrary attacker-controlled redirect URIs.
_TUNNEL_HOST_RE = re.compile(
    r"^("
    r"localhost|"
    r"127\.0\.0\.1|"
    r"[a-z0-9-]+\.ngrok-free\.app|"
    r"[a-z0-9-]+\.ngrok\.io|"
    r"[a-z0-9-]+\.ngrok\.app|"
    r"[a-z0-9-]+\.ngrok\.dev"
    r")$",
    re.IGNORECASE,
)


def google_oauth_configured() -> bool:
    """
    Check whether Google sign-in is enabled.

    Created so auth.py and the login UI can show/hide the Google button and skip
    OAuth logic when GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not in .env.
    """
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def google_sub_to_user_id(google_sub: str) -> str:
    """
    Map a Google account to a stable Termai user_id (e.g. g_a1b2c3d4e5f67890).

    Created because Termai usernames must match paths.USER_ID_RE / GOOGLE_USER_ID_RE.
    Google 'sub' is opaque and can contain chars unsuitable as folder names, so we
    hash it to a fixed g_<16-hex> id used for workspaces/, memory/, and users.json.
    """
    digest = hashlib.sha256(google_sub.encode("utf-8")).hexdigest()[:16]
    return f"g_{digest}"


def _normalize_redirect_uri(uri: str) -> str:
    """
    Strip whitespace and trailing slashes from redirect URIs.

    Created because Google requires an exact string match; http://localhost:8501/
    and http://localhost:8501 would otherwise be treated as different URIs.
    """
    return uri.strip().rstrip("/")


def _redirect_uri_allowed(uri: str) -> bool:
    """
    Decide whether a redirect URI is safe to use in OAuth requests.

    Created as a security guard: only the URI from GOOGLE_REDIRECT_URI, the ngrok
    URL from TERMAI_NGROK_URL, or (when dynamic redirect is on) known local/tunnel
    hosts are accepted. Blocks open-redirect style abuse via crafted state/URI.
    """
    uri = _normalize_redirect_uri(uri)
    if not uri.startswith(("http://", "https://")):
        return False

    configured = _normalize_redirect_uri(GOOGLE_REDIRECT_URI or "")
    if configured and uri == configured:
        return True

    ngrok_url = _normalize_redirect_uri(NGROK_PUBLIC_URL or "")
    if ngrok_url and uri == ngrok_url:
        return True

    if not OAUTH_DYNAMIC_REDIRECT:
        return False

    parsed = urllib.parse.urlparse(uri)
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if _TUNNEL_HOST_RE.match(host):
        return True
    return host.endswith(".ngrok-free.app") or host.endswith(".ngrok.io")


def streamlit_request_headers() -> dict[str, str]:
    """
    Read HTTP headers from the current Streamlit browser session.

    Created because Streamlit does not expose request.host directly. We need Host /
    X-Forwarded-Host to detect ngrok or reverse-proxy URLs when resolving the OAuth
    redirect URI. Returns {} if headers cannot be read (falls back to .env URI).
    """
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        from streamlit.web.server.browser_websocket_handler import (
            BrowserWebSocketHandler,
        )

        ctx = get_script_run_ctx()
        if ctx and ctx.session_id:
            session = BrowserWebSocketHandler.get_session(ctx.session_id)
            if session and hasattr(session, "client"):
                return dict(session.client.request.headers)
    except Exception:
        pass
    return {}


def _is_ngrok_host(host: str) -> bool:
    """
    Return True if the hostname looks like an ngrok tunnel domain.

    Created for optional public demos: when TERMAI_OAUTH_DYNAMIC_REDIRECT=true and
    the user accesses the app via ngrok, get_effective_redirect_uri() uses the ngrok
    URL so Google redirects back to the tunnel, not localhost. Not used for normal
    local dev when TERMAI_OAUTH_DYNAMIC_REDIRECT=false (the default).
    """
    host = host.lower().split(":")[0]
    return (
        ".ngrok" in host
        or host.endswith(".ngrok-free.app")
        or host.endswith(".ngrok.io")
        or host.endswith(".ngrok.app")
        or host.endswith(".ngrok.dev")
    )


def get_effective_redirect_uri(headers: dict[str, str] | None = None) -> str:
    """
    Choose the redirect URI sent to Google for this login attempt.

    Created to avoid redirect_uri_mismatch errors:
      - Default (local dev): always GOOGLE_REDIRECT_URI from .env (e.g. http://localhost:8501).
      - With TERMAI_NGROK_URL set: use that public URL (must be registered in Google Console).
      - With dynamic redirect + ngrok host in request: auto-detect ngrok URL from headers.

    The chosen URI is stored inside signed OAuth state so the token exchange uses
    the same URI Google saw at authorization time.
    """
    headers = headers or {}
    configured = _normalize_redirect_uri(GOOGLE_REDIRECT_URI or "http://localhost:8501")

    if NGROK_PUBLIC_URL:
        candidate = _normalize_redirect_uri(NGROK_PUBLIC_URL)
        if _redirect_uri_allowed(candidate):
            return candidate

    if OAUTH_DYNAMIC_REDIRECT:
        forwarded_host = headers.get("X-Forwarded-Host") or headers.get("Host") or ""
        host_only = forwarded_host.split(",")[0].strip().split(":")[0]
        if host_only and _is_ngrok_host(host_only):
            forwarded_proto = headers.get("X-Forwarded-Proto", "https")
            host = forwarded_host.split(",")[0].strip()
            proto = forwarded_proto.split(",")[0].strip()
            candidate = _normalize_redirect_uri(f"{proto}://{host}")
            if _redirect_uri_allowed(candidate):
                return candidate

    return configured


def is_ngrok_request(headers: dict[str, str] | None = None) -> bool:
    """
    Return True if the current request Host header contains 'ngrok'.

    Created for optional UI/logging (e.g. show a 'tunnel mode' banner). Not required
    for the core OAuth flow; get_effective_redirect_uri() uses _is_ngrok_host instead.
    """
    headers = headers or {}
    host = (headers.get("X-Forwarded-Host") or headers.get("Host") or "").lower()
    return ".ngrok" in host


def _sign_state(payload: dict) -> str:
    """
    Build a tamper-proof OAuth state parameter (base64 JSON + HMAC signature).

    Created because Google returns 'state' unchanged after login. We embed the
    redirect_uri and a random nonce inside state so attackers cannot swap redirect
    URIs between the authorize step and the token exchange step.
    """
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(
        OAUTH_STATE_SECRET.encode("utf-8"),
        raw,
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(raw + b"." + sig).decode("ascii")


def _verify_state(state: str) -> dict | None:
    """
    Parse and verify the signed OAuth state from Google's callback.

    Created as the counterpart to _sign_state(); returns None if the state was
    forged or corrupted, which causes complete_google_oauth() to fail safely.
    """
    try:
        decoded = base64.urlsafe_b64decode(state.encode("ascii"))
        raw, sig = decoded.rsplit(b".", 1)
        expected = hmac.new(
            OAUTH_STATE_SECRET.encode("utf-8"),
            raw,
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def build_google_auth_url(redirect_uri: str) -> str:
    """
    Build the Google authorization URL for the "Continue with Google" button.

    Created so auth.render_login_page() can link the user to Google with the correct
    client_id, redirect_uri, scopes (email + profile), and signed state.
    """
    redirect_uri = _normalize_redirect_uri(redirect_uri)
    if not _redirect_uri_allowed(redirect_uri):
        raise ValueError(f"Redirect URI not allowed: {redirect_uri}")

    state = _sign_state({
        "nonce": secrets.token_urlsafe(16),
        "redirect_uri": redirect_uri,
    })
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def _post_form(url: str, data: dict) -> dict:
    """
    POST application/x-www-form-urlencoded data and parse JSON response.

    Created as a small helper for the token exchange step (no extra HTTP library).
    Used once: exchange authorization code for access_token at GOOGLE_TOKEN_URL.
    """
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google token error ({e.code}): {detail}") from e


def _get_json(url: str, access_token: str) -> dict:
    """
    GET a JSON API with Bearer token authorization.

    Created as a small helper to fetch the user's profile from GOOGLE_USERINFO_URL
    after we have an access_token from the code exchange.
    """
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google userinfo error ({e.code}): {detail}") from e


def complete_google_oauth(code: str, state: str) -> dict | None:
    """
    Finish login after Google redirects back with ?code=...&state=...

    Created as the main callback handler called from auth.handle_google_oauth_callback():
      1. Verify state and recover the redirect_uri used at login start.
      2. Exchange code for access_token at Google.
      3. Fetch name/email/sub from userinfo.
      4. Optionally enforce TERMAI_GOOGLE_ALLOWED_DOMAINS.
      5. Return {user_id, name, email, google_sub} for auth.py to save and log in.

    Returns None on any failure; raises PermissionError if email domain is blocked.
    """
    if not google_oauth_configured():
        return None

    payload = _verify_state(state)
    if not payload or "redirect_uri" not in payload:
        return None

    redirect_uri = _normalize_redirect_uri(payload["redirect_uri"])
    if not _redirect_uri_allowed(redirect_uri):
        return None

    token_data = _post_form(
        GOOGLE_TOKEN_URL,
        {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    access_token = token_data.get("access_token")
    if not access_token:
        return None

    profile = _get_json(GOOGLE_USERINFO_URL, access_token)
    google_sub = profile.get("sub")
    email = (profile.get("email") or "").strip().lower()
    name = (profile.get("name") or email.split("@")[0] or "Google User").strip()

    if not google_sub:
        return None

    if GOOGLE_ALLOWED_DOMAINS and email:
        domain = email.rsplit("@", 1)[-1]
        if domain not in GOOGLE_ALLOWED_DOMAINS:
            raise PermissionError(
                f"Email domain {domain!r} is not allowed for sign-in."
            )

    user_id = google_sub_to_user_id(google_sub)
    return {
        "user_id": user_id,
        "name": name,
        "email": email,
        "google_sub": google_sub,
    }
