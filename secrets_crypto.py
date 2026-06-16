"""
Symmetric encryption-at-rest for per-user secrets (API keys in users.json).

The encryption key is resolved with zero manual setup:
  1. TERMAI_SECRET_KEY env var, if set (use this in production), else
  2. a local key file (.termai_key, gitignored), auto-created on first use.

Secrets are encrypted before being written to users.json and decrypted in
memory when an agent run needs them. This keeps API keys out of plaintext on
disk, so an accidental commit, a backup, or a stray file read yields ciphertext.

It does NOT protect against a process that can read the server's own key
(see README security notes — that needs execution sandboxing).

Existing plaintext keys keep working and migrate to ciphertext on next save.
"""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

# Marks an encrypted value so plaintext (legacy) keys are distinguishable.
_PREFIX = "enc:"

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_KEY_FILE = os.path.join(_BASE_DIR, ".termai_key")

_fernet_cache: Fernet | None = None


def _load_or_create_key() -> bytes:
    """Return the Fernet key: env var, else local key file (auto-created)."""
    env_key = os.getenv("TERMAI_SECRET_KEY", "").strip()
    if env_key:
        return env_key.encode()

    if os.path.isfile(_KEY_FILE):
        with open(_KEY_FILE, "rb") as f:
            return f.read().strip()

    key = Fernet.generate_key()
    # Write owner-only so other accounts on the host cannot read it.
    fd = os.open(_KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    return key


def _fernet() -> Fernet:
    """Cached Fernet instance built from the resolved key."""
    global _fernet_cache
    if _fernet_cache is None:
        try:
            _fernet_cache = Fernet(_load_or_create_key())
        except (ValueError, TypeError) as e:
            raise RuntimeError(
                "Encryption key is invalid. If TERMAI_SECRET_KEY is set it must "
                "be a valid Fernet key (python -c \"from cryptography.fernet "
                "import Fernet; print(Fernet.generate_key().decode())\")."
            ) from e
    return _fernet_cache


def is_encrypted(value: str | None) -> bool:
    """True if the stored value is in encrypted form."""
    return bool(value) and value.startswith(_PREFIX)


def encrypt_secret(plain: str) -> str:
    """Encrypt a plaintext secret for storage in users.json."""
    if not plain:
        return plain
    return _PREFIX + _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(stored: str) -> str:
    """
    Decrypt a stored secret. Legacy plaintext (no prefix) is returned as-is.

    Raises RuntimeError if an encrypted value cannot be decrypted (the key was
    changed or lost) — a loud failure beats silently using a bad credential.
    """
    if not is_encrypted(stored):
        return stored
    try:
        return _fernet().decrypt(stored[len(_PREFIX):].encode()).decode()
    except InvalidToken as e:
        raise RuntimeError(
            "Cannot decrypt stored API key — the encryption key does not match "
            "the one used to encrypt it. Restore the original key/.termai_key, "
            "or have the user re-enter their API key in Settings."
        ) from e


def ensure_encrypted(stored: str) -> str:
    """Encrypt a value if it is still plaintext; leave ciphertext untouched."""
    if is_encrypted(stored):
        return stored
    return encrypt_secret(stored)
