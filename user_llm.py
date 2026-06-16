"""
Per-user LLM settings stored in users.json under each user's ``llm`` key.

Falls back to server defaults from .env when a user has no personal API key.
"""

from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI
from rich.console import Console

from config import (
    FALLBACK_MODEL,
    MAX_OUTPUT_TOKENS,
    MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    PROVIDER_PRESETS,
)
from paths import validate_user_id
from secrets_crypto import decrypt_secret, encrypt_secret, ensure_encrypted

console = Console()

VALID_PROVIDERS = frozenset(PROVIDER_PRESETS)


@dataclass(frozen=True)
class ResolvedLLMConfig:
    """Effective LLM credentials for one agent run."""

    source: str  # "user" | "server"
    provider: str
    api_key: str
    base_url: str
    model: str
    fallback_model: str | None
    max_output_tokens: int | None


def _make_client(api_key: str | None, base_url: str | None) -> OpenAI | None:
    if not api_key or not api_key.strip():
        return None
    return OpenAI(
        api_key=api_key.strip(),
        base_url=(base_url or "https://api.openai.com/v1").rstrip("/"),
    )


def mask_api_key(api_key: str) -> str:
    """Masked preview: first 2 and last 2 characters, e.g. ``sk••••3f``."""
    key = (api_key or "").strip()
    if len(key) <= 6:
        return "••••••••"
    return f"{key[:2]}••••{key[-2:]}"


def _normalize_provider(provider: str) -> str:
    provider = (provider or "openai").strip().lower()
    if provider not in VALID_PROVIDERS:
        raise ValueError(f"Invalid provider: {provider!r}")
    return provider


def _preset_base_url(provider: str) -> str:
    return PROVIDER_PRESETS[provider]["base_url"]


def _normalize_max_output_tokens(value, *, default: int | None = None) -> int | None:
    """Parse max output tokens; None means no cap (caller may substitute default)."""
    if value is None or value == "":
        return default
    try:
        n = int(value)
    except (TypeError, ValueError) as e:
        raise ValueError("Max output tokens must be a whole number.") from e
    if n <= 0:
        return default
    if n < 16:
        raise ValueError("Max output tokens must be at least 16.")
    if n > 65536:
        raise ValueError("Max output tokens cannot exceed 65536.")
    return n


def _effective_max_output_tokens(llm: dict | None) -> int | None:
    """User-stored cap, else server ``TERMAI_MAX_OUTPUT_TOKENS`` (0 = uncapped)."""
    if llm and llm.get("max_output_tokens") is not None:
        stored = _normalize_max_output_tokens(llm.get("max_output_tokens"), default=None)
        if stored is not None:
            return stored
    if MAX_OUTPUT_TOKENS > 0:
        return MAX_OUTPUT_TOKENS
    return None


def _load_raw_users() -> dict:
    from auth import _load_users_raw

    return _load_users_raw()


def _save_raw_users(data: dict) -> None:
    from auth import _save_users_raw

    _save_users_raw(data)


def get_user_llm(user_id: str) -> dict | None:
    """Return stored ``llm`` block for a user, or None."""
    user_id = validate_user_id(user_id)
    info = _load_raw_users().get(user_id)
    if not isinstance(info, dict):
        return None
    llm = info.get("llm")
    if not isinstance(llm, dict):
        return None
    llm = dict(llm)
    if llm.get("api_key"):
        llm["api_key"] = decrypt_secret(llm["api_key"])  # stored encrypted at rest
    return llm


def save_user_llm(
    user_id: str,
    *,
    provider: str,
    api_key: str,
    base_url: str,
    model: str,
    fallback_model: str = "",
    max_output_tokens: int | str | None = None,
) -> None:
    """Persist personal LLM settings. Empty ``api_key`` keeps the existing key."""
    user_id = validate_user_id(user_id)
    provider = _normalize_provider(provider)
    model = (model or "").strip()
    if not model:
        raise ValueError("Model is required.")

    base_url = (base_url or "").strip().rstrip("/")
    if not base_url:
        if provider == "custom":
            raise ValueError("Base URL is required for a custom provider.")
        base_url = _preset_base_url(provider)
    elif not base_url.startswith(("http://", "https://")):
        raise ValueError("Base URL must start with http:// or https://")

    raw = _load_raw_users()
    info = raw.get(user_id)
    if not isinstance(info, dict):
        raise ValueError(f"Unknown user: {user_id}")

    existing = info.get("llm") if isinstance(info.get("llm"), dict) else {}
    # ``existing`` holds the raw (encrypted) value from disk. A newly entered
    # key arrives as plaintext and is encrypted; an unchanged key keeps its
    # stored ciphertext (legacy plaintext is migrated to ciphertext here).
    new_key = (api_key or "").strip()
    if new_key:
        stored_key = encrypt_secret(new_key)
    else:
        existing_key = (existing.get("api_key") or "").strip()
        if not existing_key:
            raise ValueError("API key is required.")
        stored_key = ensure_encrypted(existing_key)

    if max_output_tokens is None or max_output_tokens == "":
        token_cap = _normalize_max_output_tokens(
            existing.get("max_output_tokens"),
            default=MAX_OUTPUT_TOKENS,
        )
    else:
        token_cap = _normalize_max_output_tokens(max_output_tokens, default=MAX_OUTPUT_TOKENS)

    info["llm"] = {
        "provider": provider,
        "api_key": stored_key,
        "base_url": base_url,
        "model": model,
        "fallback_model": (fallback_model or "").strip(),
        "max_output_tokens": token_cap,
    }
    raw[user_id] = info
    _save_raw_users(raw)


def clear_user_llm(user_id: str) -> None:
    """Remove personal LLM settings; user falls back to server defaults."""
    user_id = validate_user_id(user_id)
    raw = _load_raw_users()
    info = raw.get(user_id)
    if not isinstance(info, dict):
        return
    info.pop("llm", None)
    raw[user_id] = info
    _save_raw_users(raw)


def resolve_llm_for_run(user_id: str) -> ResolvedLLMConfig:
    """Merge user settings with server .env defaults."""
    user_id = validate_user_id(user_id)
    llm = get_user_llm(user_id)
    if llm and (llm.get("api_key") or "").strip():
        provider = _normalize_provider(llm.get("provider", "openai"))
        base_url = (llm.get("base_url") or "").strip().rstrip("/")
        if not base_url:
            base_url = _preset_base_url(provider)
        fallback = (llm.get("fallback_model") or "").strip() or None
        return ResolvedLLMConfig(
            source="user",
            provider=provider,
            api_key=llm["api_key"].strip(),
            base_url=base_url,
            model=(llm.get("model") or MODEL).strip(),
            fallback_model=fallback,
            max_output_tokens=_effective_max_output_tokens(llm),
        )

    if OPENAI_API_KEY and OPENAI_API_KEY.strip():
        return ResolvedLLMConfig(
            source="server",
            provider="openai",
            api_key=OPENAI_API_KEY.strip(),
            base_url=(OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/"),
            model=MODEL,
            fallback_model=FALLBACK_MODEL if OPENROUTER_API_KEY else None,
            max_output_tokens=_effective_max_output_tokens(None),
        )

    if OPENROUTER_API_KEY and OPENROUTER_API_KEY.strip():
        return ResolvedLLMConfig(
            source="server",
            provider="openrouter",
            api_key=OPENROUTER_API_KEY.strip(),
            base_url=(OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1").rstrip("/"),
            model=FALLBACK_MODEL,
            fallback_model=None,
            max_output_tokens=_effective_max_output_tokens(None),
        )

    raise RuntimeError(
        "No API key configured. Add your key in Settings, or set OPENAI_API_KEY "
        "(and OPENAI_BASE_URL) in .env."
    )


def llm_ready(user_id: str) -> bool:
    """True when the user or server has credentials to call an LLM."""
    try:
        resolve_llm_for_run(user_id)
        return True
    except RuntimeError:
        return False


def llm_status_summary(user_id: str) -> dict:
    """Status dict for sidebar and Settings page."""
    try:
        resolved = resolve_llm_for_run(user_id)
    except RuntimeError:
        resolved = None

    llm = get_user_llm(user_id)
    if llm and (llm.get("api_key") or "").strip():
        provider = llm.get("provider", "openai")
        label = PROVIDER_PRESETS.get(provider, {}).get("label", provider)
        return {
            "using_personal": True,
            "provider": provider,
            "provider_label": label,
            "model": llm.get("model", MODEL),
            "masked_key": mask_api_key(llm["api_key"]),
            "base_url": llm.get("base_url", ""),
            "max_output_tokens": resolved.max_output_tokens if resolved else None,
        }

    if OPENAI_API_KEY and OPENAI_API_KEY.strip():
        return {
            "using_personal": False,
            "provider": "openai",
            "provider_label": "Server default (OpenAI)",
            "model": MODEL,
            "masked_key": "",
            "base_url": OPENAI_BASE_URL,
            "max_output_tokens": resolved.max_output_tokens if resolved else MAX_OUTPUT_TOKENS,
        }

    if OPENROUTER_API_KEY and OPENROUTER_API_KEY.strip():
        return {
            "using_personal": False,
            "provider": "openrouter",
            "provider_label": "Server default (OpenRouter)",
            "model": FALLBACK_MODEL,
            "masked_key": "",
            "base_url": OPENROUTER_BASE_URL,
            "max_output_tokens": resolved.max_output_tokens if resolved else MAX_OUTPUT_TOKENS,
        }

    return {
        "using_personal": False,
        "provider": "",
        "provider_label": "Not configured",
        "model": "",
        "masked_key": "",
        "base_url": "",
        "max_output_tokens": None,
    }


def test_llm_connection(user_id: str) -> tuple[bool, str]:
    """Lightweight API check using the user's resolved config."""
    try:
        resolved = resolve_llm_for_run(user_id)
    except RuntimeError as e:
        return False, str(e)

    client = _make_client(resolved.api_key, resolved.base_url)
    if client is None:
        return False, "No API client could be created."

    try:
        client.chat.completions.create(
            model=resolved.model,
            messages=[{"role": "user", "content": "Reply with OK"}],
            max_tokens=16,
        )
        return True, f"Connected ({resolved.model})"
    except Exception as e:
        return False, str(e)


def _apply_output_token_cap(kwargs: dict, max_output_tokens: int | None) -> dict:
    """Set max_tokens when omitted — avoids OpenRouter defaulting to 65536."""
    if kwargs.get("max_tokens") is not None:
        return kwargs
    if not max_output_tokens or max_output_tokens <= 0:
        return kwargs
    capped = dict(kwargs)
    capped["max_tokens"] = max_output_tokens
    return capped


def create_chat_completion(user_id: str, **kwargs):
    """
    Call the LLM for ``user_id``.

    User keys use only their provider (optional personal fallback model).
    Server keys use OpenAI primary with OpenRouter fallback.
    """
    resolved = resolve_llm_for_run(user_id)
    client = _make_client(resolved.api_key, resolved.base_url)
    if client is None:
        raise RuntimeError("No API client available.")

    if "model" not in kwargs or not kwargs["model"]:
        kwargs = dict(kwargs)
        kwargs["model"] = resolved.model

    kwargs = _apply_output_token_cap(kwargs, resolved.max_output_tokens)

    if resolved.source == "user":
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as primary_error:
            if resolved.fallback_model and kwargs.get("model") != resolved.fallback_model:
                console.print(
                    f"[yellow]⚠ Personal API failed, trying fallback model:[/yellow] "
                    f"{primary_error}"
                )
                retry = dict(kwargs)
                retry["model"] = resolved.fallback_model
                return client.chat.completions.create(**retry)
            raise

    # Server defaults: primary OpenAI-compatible, then OpenRouter
    try:
        return client.chat.completions.create(**kwargs)
    except Exception as primary_error:
        console.print(f"[yellow]⚠ Primary API failed:[/yellow] {primary_error}")
        if not resolved.fallback_model:
            raise
        fallback_client = _make_client(OPENROUTER_API_KEY, OPENROUTER_BASE_URL)
        if fallback_client is None:
            raise
        retry = dict(kwargs)
        retry["model"] = resolved.fallback_model
        return fallback_client.chat.completions.create(**retry)
