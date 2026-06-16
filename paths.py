"""
Filesystem paths for per-user workspaces, agent home, and task folders.

Each user gets:
  workspaces/<user_id>/           — agent home (persona .md files) + task subfolders
  memory/<user_id>.toon           — task history (see memory.py)
"""

import os
import re
from datetime import datetime

USER_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
GOOGLE_USER_ID_RE = re.compile(r"^g_[a-f0-9]{16}$")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACES_ROOT = os.path.join(BASE_DIR, "workspaces")
MEMORY_DIR = os.path.join(BASE_DIR, "memory")

_TASK_FOLDER_TS = re.compile(r"_\d{8}_\d{6}$")

# Folder names under workspaces/<user>/ that are NOT task output directories
AGENT_HOME_SUBDIRS = frozenset({"memory", "avatars", "skills", "canvas"})


def is_task_workspace_dir(name: str) -> bool:
    """True if a directory name looks like a task workspace folder, not agent infrastructure."""
    return bool(name) and not name.startswith(".") and name not in AGENT_HOME_SUBDIRS


def validate_user_id(user_id: str) -> str:
    """Normalize and validate username or Google-derived id; raises ValueError if invalid."""
    user_id = user_id.strip().lower()
    if not (USER_ID_RE.match(user_id) or GOOGLE_USER_ID_RE.match(user_id)):
        raise ValueError(f"Invalid user_id: {user_id!r}")
    return user_id


def user_workspace_root(user_id: str) -> str:
    """Return workspaces/<user_id>/ and create it if needed."""
    user_id = validate_user_id(user_id)
    path = os.path.join(WORKSPACES_ROOT, user_id)
    os.makedirs(path, exist_ok=True)
    return path


def user_agent_home(user_id: str) -> str:
    """Per-user home for persona/bootstrap markdown (AGENTS.md, SOUL.md, etc.)."""
    return user_workspace_root(user_id)


def user_skills_dir(user_id: str) -> str:
    """Per-user private skills: workspaces/<user_id>/skills/."""
    user_id = validate_user_id(user_id)
    path = os.path.join(user_workspace_root(user_id), "skills")
    os.makedirs(path, exist_ok=True)
    return path


def make_task_workspace(user_id: str, task: str) -> str:
    """Create workspaces/<user_id>/<task_slug>_<timestamp>/ for one run."""
    user_id = validate_user_id(user_id)
    slug = re.sub(r"[^a-z0-9]+", "_", task.lower()).strip("_")[:40] or "task"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = os.path.join(user_workspace_root(user_id), f"{slug}_{stamp}")
    os.makedirs(folder, exist_ok=True)
    return folder


def workspace_display_name(workspace: str) -> str:
    """Friendly task label for UI — never exposes filesystem paths."""
    ws = (workspace or "").strip()
    if not ws:
        return "Task workspace"
    if ws.startswith("(chat"):
        return "Chat only"
    folder = os.path.basename(ws.rstrip("/"))
    label = _TASK_FOLDER_TS.sub("", folder).replace("_", " ").strip()
    return label or "Task workspace"


def sanitize_paths_for_ui(text: str) -> str:
    """Redact absolute project paths from user-visible terminal/UI text."""
    if not text:
        return text
    result = text
    ws_pattern = re.compile(re.escape(WORKSPACES_ROOT) + r"(?:/[^/\s\"'<>]+)+")
    result = ws_pattern.sub(lambda m: workspace_display_name(m.group(0)), result)
    mem_pattern = re.compile(re.escape(MEMORY_DIR) + r"/[^\s\"'<>]+")
    result = mem_pattern.sub("memory store", result)
    base_pattern = re.compile(re.escape(BASE_DIR) + r"/[^\s\"'<>]+")
    result = base_pattern.sub("[private]", result)
    return result
