"""
OpenClaw-style persona/bootstrap files per user agent home.

Templates live in templates/persona/; copies are seeded under workspaces/<user>/.
build_system_prompt() injects them into the LLM system message.
"""

import os
from datetime import datetime, timedelta

from paths import user_agent_home, validate_user_id

USER_DISPLAY_PLACEHOLDER = "{{USER_DISPLAY_NAME}}"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates", "persona")

BOOTSTRAP_MAX_CHARS = 20_000
BOOTSTRAP_TOTAL_MAX_CHARS = 60_000

# Loaded every session (in order). Mirrors OpenClaw workspace bootstrap files.
CORE_FILES = [
    ("AGENTS.md", "Operating instructions"),
    ("SOUL.md", "Persona and tone"),
    ("USER.md", "User profile"),
    ("IDENTITY.md", "Agent identity"),
    ("TOOLS.md", "Local tool notes"),
]

OPTIONAL_FILES = [
    ("HEARTBEAT.md", "Heartbeat checklist"),
    ("BOOTSTRAP.md", "First-run ritual"),
    ("MEMORY.md", "Long-term curated memory"),
]

EDITABLE_FILES = [name for name, _ in CORE_FILES + OPTIONAL_FILES]


def _apply_user_display(template: str, display_name: str) -> str:
    """Substitute {{USER_DISPLAY_NAME}} in USER.md template."""
    result = template.replace(USER_DISPLAY_PLACEHOLDER, display_name)
    if USER_DISPLAY_PLACEHOLDER in result:
        raise ValueError("USER.md template contains unresolved display-name placeholder")
    return result


def _template_path(filename: str) -> str:
    """Path to shipped template for a bootstrap filename."""
    return os.path.join(TEMPLATES_DIR, filename)


def _read_file(path: str) -> str | None:
    """Read UTF-8 file or None if missing."""
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _truncate(text: str, limit: int) -> str:
    """Cap bootstrap section size for prompt token budget."""
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n\n[... truncated ...]"


def _heartbeat_has_content(text: str) -> bool:
    """Skip HEARTBEAT.md when it is empty or comments-only (OpenClaw behavior)."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return True
    return False


def _daily_memory_paths(agent_home: str) -> list[tuple[str, str]]:
    """Today and yesterday daily memory files, if they exist."""
    memory_dir = os.path.join(agent_home, "memory")
    paths: list[tuple[str, str]] = []
    for offset in (0, 1):
        day = datetime.now() - timedelta(days=offset)
        name = f"{day.strftime('%Y-%m-%d')}.md"
        path = os.path.join(memory_dir, name)
        if os.path.isfile(path):
            paths.append((f"memory/{name}", path))
    return paths


def ensure_persona_files(user_id: str, display_name: str | None = None) -> str:
    """
    Seed missing bootstrap files from templates. Never overwrites existing files.
    Returns the user's agent home path.
    """
    user_id = validate_user_id(user_id)
    agent_home = user_agent_home(user_id)
    os.makedirs(os.path.join(agent_home, "memory"), exist_ok=True)

    label = display_name or user_id
    for filename, _ in CORE_FILES + OPTIONAL_FILES:
        dest = os.path.join(agent_home, filename)
        if os.path.exists(dest):
            continue
        template = _read_file(_template_path(filename))
        if template is None:
            continue
        if filename == "USER.md":
            template = _apply_user_display(template, label)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(template)

    return agent_home


def read_persona_file(user_id: str, filename: str) -> str | None:
    """Read one editable bootstrap file for the Persona UI."""
    user_id = validate_user_id(user_id)
    if filename not in EDITABLE_FILES:
        raise ValueError(f"Invalid persona file: {filename!r}")
    return _read_file(os.path.join(user_agent_home(user_id), filename))


def write_persona_file(user_id: str, filename: str, content: str) -> None:
    """Save edited bootstrap content from the Persona page."""
    user_id = validate_user_id(user_id)
    if filename not in EDITABLE_FILES:
        raise ValueError(f"Invalid persona file: {filename!r}")
    agent_home = user_agent_home(user_id)
    os.makedirs(agent_home, exist_ok=True)
    path = os.path.join(agent_home, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def reset_persona_file(user_id: str, filename: str, display_name: str | None = None) -> None:
    """Restore a single file from the shipped template."""
    user_id = validate_user_id(user_id)
    if filename not in EDITABLE_FILES:
        raise ValueError(f"Invalid persona file: {filename!r}")
    template = _read_file(_template_path(filename))
    if template is None:
        raise FileNotFoundError(f"No template for {filename}")
    if filename == "USER.md":
        template = _apply_user_display(template, display_name or user_id)
    write_persona_file(user_id, filename, template)


def list_persona_files(user_id: str) -> list[dict]:
    """Metadata for UI/CLI listing."""
    user_id = validate_user_id(user_id)
    agent_home = user_agent_home(user_id)
    rows = []
    for filename, description in CORE_FILES + OPTIONAL_FILES:
        path = os.path.join(agent_home, filename)
        rows.append({
            "file": filename,
            "description": description,
            "path": path,
            "exists": os.path.isfile(path),
            "core": filename in {n for n, _ in CORE_FILES},
        })
    return rows


def build_project_context(user_id: str, *, include_optional: bool = True) -> str:
    """
    Build OpenClaw-style Project Context block for system prompt injection.
    Missing core files get a marker; optional files are omitted when absent.
    """
    user_id = validate_user_id(user_id)
    agent_home = user_agent_home(user_id)
    sections: list[str] = []
    total_chars = 0

    def _add_section(label: str, body: str) -> bool:
        nonlocal total_chars
        body = _truncate(body.strip(), BOOTSTRAP_MAX_CHARS)
        block = f"## {label}\n\n{body}"
        if total_chars + len(block) > BOOTSTRAP_TOTAL_MAX_CHARS:
            remaining = BOOTSTRAP_TOTAL_MAX_CHARS - total_chars
            if remaining < 100:
                return False
            block = _truncate(block, remaining)
        sections.append(block)
        total_chars += len(block)
        return True

    for filename, _description in CORE_FILES:
        content = _read_file(os.path.join(agent_home, filename))
        if content is None:
            body = f"[{filename} not found — using defaults]"
        else:
            body = content
        if not _add_section(filename, body):
            break

    if include_optional:
        for filename, _description in OPTIONAL_FILES:
            path = os.path.join(agent_home, filename)
            content = _read_file(path)
            if content is None:
                continue
            if filename == "HEARTBEAT.md" and not _heartbeat_has_content(content):
                continue
            if not _add_section(filename, content):
                break

        for rel_path, abs_path in _daily_memory_paths(agent_home):
            content = _read_file(abs_path)
            if content and content.strip():
                if not _add_section(rel_path, content):
                    break

    if not sections:
        return ""
    return "# Project Context\n\n" + "\n\n".join(sections)


def build_system_prompt(
    user_id: str,
    base_prompt: str,
    *,
    chat_only: bool = False,
    display_name: str | None = None,
) -> str:
    """
    Combine runtime system prompt with injected bootstrap files.
    chat_only: lighter injection (SOUL + USER + IDENTITY) for simple Q&A.
    """
    from config import SYSTEM_PROMPT

    base = base_prompt or SYSTEM_PROMPT
    ensure_persona_files(user_id, display_name)
    agent_home = user_agent_home(user_id)

    if chat_only:
        parts = [base, f"\n\n# Agent home\n{agent_home}"]
        for filename in ("SOUL.md", "USER.md", "IDENTITY.md"):
            content = _read_file(os.path.join(agent_home, filename))
            if content and content.strip():
                parts.append(f"\n\n## {filename}\n\n{_truncate(content.strip(), 8000)}")
        return "".join(parts)

    ctx = build_project_context(user_id)
    if ctx:
        return f"{base}\n\n{ctx}\n\n# Agent home\n{agent_home}"
    return f"{base}\n\n# Agent home\n{agent_home}"
