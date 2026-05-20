"""Project paths and one-time legacy layout migration."""

import os
import re
import shutil
from datetime import datetime

from auth import load_users

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACES_ROOT = os.path.join(BASE_DIR, "workspaces")
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
LEGACY_MEMORY_FILE = os.path.join(BASE_DIR, "memory.toon")
MIGRATION_FLAG = os.path.join(MEMORY_DIR, ".migrated")
WORKSPACE_MIGRATION_FLAG = os.path.join(WORKSPACES_ROOT, ".migrated")

USER_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")


def validate_user_id(user_id: str) -> str:
    user_id = user_id.strip().lower()
    if not USER_ID_RE.match(user_id):
        raise ValueError(f"Invalid user_id: {user_id!r}")
    return user_id


def known_user_ids() -> set[str]:
    return set(load_users().keys())


def user_workspace_root(user_id: str) -> str:
    user_id = validate_user_id(user_id)
    path = os.path.join(WORKSPACES_ROOT, user_id)
    os.makedirs(path, exist_ok=True)
    return path


def make_task_workspace(user_id: str, task: str) -> str:
    """workspaces/<user_id>/<task_slug>_<timestamp>/"""
    user_id = validate_user_id(user_id)
    slug = re.sub(r"[^a-z0-9]+", "_", task.lower()).strip("_")[:40] or "task"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = os.path.join(user_workspace_root(user_id), f"{slug}_{stamp}")
    os.makedirs(folder, exist_ok=True)
    return folder


def _legacy_default_user() -> str:
    return os.getenv("TERMAI_LEGACY_USER", "alice")


def migrate_legacy_workspaces() -> None:
    """Move workspaces/<task>/ → workspaces/<user>/<task>/ for old flat layout."""
    if os.path.exists(WORKSPACE_MIGRATION_FLAG):
        return
    os.makedirs(WORKSPACES_ROOT, exist_ok=True)
    users = known_user_ids()
    default_user = _legacy_default_user()
    if default_user not in users and users:
        default_user = next(iter(sorted(users)))

    for name in os.listdir(WORKSPACES_ROOT):
        if name in users or name.startswith("."):
            continue
        src = os.path.join(WORKSPACES_ROOT, name)
        if not os.path.isdir(src):
            continue
        dest_root = user_workspace_root(default_user)
        dest = os.path.join(dest_root, name)
        if os.path.exists(dest):
            continue
        shutil.move(src, dest)

    with open(WORKSPACE_MIGRATION_FLAG, "w") as f:
        f.write("ok\n")


def migrate_legacy_memory() -> None:
    """Import root memory.toon into per-user files (legacy → alice by default)."""
    if os.path.exists(MIGRATION_FLAG):
        return
    os.makedirs(MEMORY_DIR, exist_ok=True)

    if os.path.exists(LEGACY_MEMORY_FILE):
        import toon

        legacy = toon.loads(open(LEGACY_MEMORY_FILE).read())
        tasks = legacy.get("tasks", [])
        if tasks:
            default_user = _legacy_default_user()
            users = known_user_ids()
            if default_user not in users and users:
                default_user = next(iter(sorted(users)))

            per_user_path = os.path.join(MEMORY_DIR, f"{default_user}.toon")
            existing = {"tasks": []}
            if os.path.exists(per_user_path):
                existing = toon.loads(open(per_user_path).read())

            seen = {(t.get("task"), t.get("workspace")) for t in existing.get("tasks", [])}
            for t in tasks:
                key = (t.get("task"), t.get("workspace"))
                if key not in seen:
                    existing.setdefault("tasks", []).append(t)
                    seen.add(key)

            existing["tasks"] = existing["tasks"][-50:]
            with open(per_user_path, "w") as f:
                f.write(toon.dumps(existing))

            backup = LEGACY_MEMORY_FILE + ".bak"
            if not os.path.exists(backup):
                shutil.move(LEGACY_MEMORY_FILE, backup)

    with open(MIGRATION_FLAG, "w") as f:
        f.write("ok\n")


def run_startup_migrations() -> None:
    migrate_legacy_workspaces()
    migrate_legacy_memory()
