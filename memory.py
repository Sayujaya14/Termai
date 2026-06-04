import os
import re
import threading
from datetime import datetime

import toon

from paths import MEMORY_DIR, user_workspace_root, validate_user_id, is_task_workspace_dir

_WORKSPACE_TS = re.compile(r"_\d{8}_\d{6}$")

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _user_lock(user_id: str) -> threading.Lock:
    with _locks_guard:
        if user_id not in _locks:
            _locks[user_id] = threading.Lock()
        return _locks[user_id]


def _memory_path(user_id: str) -> str:
    user_id = validate_user_id(user_id)
    os.makedirs(MEMORY_DIR, exist_ok=True)
    return os.path.join(MEMORY_DIR, f"{user_id}.toon")


def _load(user_id: str) -> dict:
    path = _memory_path(user_id)
    if os.path.exists(path):
        with open(path, "r") as f:
            return toon.loads(f.read())
    return {"tasks": []}


def _save(user_id: str, data: dict):
    path = _memory_path(user_id)
    with open(path, "w") as f:
        f.write(toon.dumps(data))


def save_task(user_id: str, task: str, workspace: str, summary: str = ""):
    user_id = validate_user_id(user_id)
    with _user_lock(user_id):
        data = _load(user_id)
        data["tasks"].append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "task": task,
            "workspace": workspace,
            "summary": summary,
        })
        data["tasks"] = data["tasks"][-20:]
        _save(user_id, data)


def update_summary(user_id: str, workspace: str, summary: str):
    """Update the most recent task matching this workspace path."""
    user_id = validate_user_id(user_id)
    with _user_lock(user_id):
        data = _load(user_id)
        for t in reversed(data["tasks"]):
            if t.get("workspace") == workspace:
                t["summary"] = summary[:200]
                break
        _save(user_id, data)


def get_memory_context(user_id: str) -> str:
    user_id = validate_user_id(user_id)
    data = _load(user_id)
    lines = []

    if data["tasks"]:
        lines.append("Previous tasks:")
        for t in data["tasks"][-5:]:
            summary = f" → {t['summary']}" if t.get("summary") else ""
            lines.append(f"  [{t['timestamp']}] {t['task']}{summary}")
            lines.append(f"    Workspace: {t['workspace']}")

    return "\n".join(lines) if lines else ""


def _task_label_from_folder(folder_name: str) -> str:
    label = _WORKSPACE_TS.sub("", folder_name)
    return label.replace("_", " ").strip() or folder_name


def sync_workspaces_to_memory(user_id: str) -> None:
    """Add memory rows for workspace folders that exist on disk but were not recorded."""
    user_id = validate_user_id(user_id)
    root = user_workspace_root(user_id)
    if not os.path.isdir(root):
        return

    with _user_lock(user_id):
        data = _load(user_id)
        known_paths = {t.get("workspace", "") for t in data["tasks"]}
        known_names = {os.path.basename(p.rstrip("/")) for p in known_paths if p}

        for name in sorted(os.listdir(root)):
            if not is_task_workspace_dir(name):
                continue
            path = os.path.join(root, name)
            if not os.path.isdir(path):
                continue
            if path in known_paths or name in known_names:
                continue
            data["tasks"].append({
                "timestamp": datetime.fromtimestamp(os.path.getmtime(path)).strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "task": _task_label_from_folder(name),
                "workspace": path,
                "summary": "(recovered from workspace folder on disk)",
            })
        data["tasks"] = data["tasks"][-20:]
        _save(user_id, data)


def get_all_tasks(user_id: str) -> list:
    user_id = validate_user_id(user_id)
    sync_workspaces_to_memory(user_id)
    return _load(user_id)["tasks"]
