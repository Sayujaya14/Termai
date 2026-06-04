"""Project paths for per-user workspaces."""

import os
import re
from datetime import datetime

USER_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACES_ROOT = os.path.join(BASE_DIR, "workspaces")
MEMORY_DIR = os.path.join(BASE_DIR, "memory")

# Subdirs of the user agent home that are not task workspaces
AGENT_HOME_SUBDIRS = frozenset({"memory", "avatars", "skills", "canvas"})


def is_task_workspace_dir(name: str) -> bool:
    return bool(name) and not name.startswith(".") and name not in AGENT_HOME_SUBDIRS


def validate_user_id(user_id: str) -> str:
    user_id = user_id.strip().lower()
    if not USER_ID_RE.match(user_id):
        raise ValueError(f"Invalid user_id: {user_id!r}")
    return user_id


def user_workspace_root(user_id: str) -> str:
    user_id = validate_user_id(user_id)
    path = os.path.join(WORKSPACES_ROOT, user_id)
    os.makedirs(path, exist_ok=True)
    return path


def user_agent_home(user_id: str) -> str:
    """Per-user agent home for persona/bootstrap files (OpenClaw-style workspace root)."""
    return user_workspace_root(user_id)


def make_task_workspace(user_id: str, task: str) -> str:
    """workspaces/<user_id>/<task_slug>_<timestamp>/"""
    user_id = validate_user_id(user_id)
    slug = re.sub(r"[^a-z0-9]+", "_", task.lower()).strip("_")[:40] or "task"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = os.path.join(user_workspace_root(user_id), f"{slug}_{stamp}")
    os.makedirs(folder, exist_ok=True)
    return folder
