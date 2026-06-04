"""
Per-user memory in memory/<user_id>.toon (TOON format).

- tasks: task titles, workspaces, summaries (Memory page)
- chat: user/assistant turns replayed on the next run (ChatGPT-style context)
"""

import os
import re
import threading
from datetime import datetime

import toon

from config import (
    CONVERSATION_ASSISTANT_MAX,
    CONVERSATION_MAX_CHARS,
    CONVERSATION_MAX_TURNS,
    CONVERSATION_USER_MAX,
)
from paths import MEMORY_DIR, user_workspace_root, validate_user_id, is_task_workspace_dir

_WORKSPACE_TS = re.compile(r"_\d{8}_\d{6}$")

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _user_lock(user_id: str) -> threading.Lock:
    """Per-user lock so concurrent agent threads do not corrupt the same .toon file."""
    with _locks_guard:
        if user_id not in _locks:
            _locks[user_id] = threading.Lock()
        return _locks[user_id]


def _memory_path(user_id: str) -> str:
    """Absolute path to memory/<user_id>.toon."""
    user_id = validate_user_id(user_id)
    os.makedirs(MEMORY_DIR, exist_ok=True)
    return os.path.join(MEMORY_DIR, f"{user_id}.toon")


def _load(user_id: str) -> dict:
    """Parse user's TOON file into {tasks: [...], chat: [...]}."""
    path = _memory_path(user_id)
    if os.path.exists(path):
        with open(path, "r") as f:
            data = toon.loads(f.read())
            data.setdefault("tasks", [])
            data.setdefault("chat", [])
            return data
    return {"tasks": [], "chat": []}


def _save(user_id: str, data: dict):
    """Write task history back to the user's TOON file."""
    path = _memory_path(user_id)
    with open(path, "w") as f:
        f.write(toon.dumps(data))


def save_task(user_id: str, task: str, workspace: str, summary: str = ""):
    """Append a new task row (keeps last 20). Called at start of each agent run."""
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
    """Formatted text of recent tasks for injection into the agent user message."""
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
    """Derive human-readable task label from workspace folder name (strip timestamp)."""
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
    """All tasks for Memory page / CLI (syncs disk first)."""
    user_id = validate_user_id(user_id)
    sync_workspaces_to_memory(user_id)
    return _load(user_id)["tasks"]


def _truncate_text(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n\n[... truncated ...]"


def _answer_from_task_summary(summary: str) -> str:
    """Extract assistant reply text stored in a task summary row."""
    s = (summary or "").strip()
    if not s or s.startswith("(recovered"):
        return ""
    if " | 🪙" in s:
        s = s.split(" | 🪙", 1)[0].strip()
    return _truncate_text(s, CONVERSATION_ASSISTANT_MAX)


def sync_tasks_to_chat(user_id: str) -> int:
    """
    Backfill @chat from @tasks so older runs count as conversation history.

    Returns number of turns added. Skips tasks already present (same user text).
    """
    user_id = validate_user_id(user_id)
    with _user_lock(user_id):
        data = _load(user_id)
        known_user_texts = {
            (t.get("user") or "").strip()
            for t in data.get("chat") or []
            if (t.get("user") or "").strip()
        }
        added = 0
        for row in data.get("tasks") or []:
            user_text = (row.get("task") or "").strip()
            if not user_text or user_text in known_user_texts:
                continue
            assistant_text = _answer_from_task_summary(row.get("summary", ""))
            if not assistant_text:
                continue
            data["chat"].append({
                "timestamp": row.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M"),
                "user": _truncate_text(user_text, CONVERSATION_USER_MAX),
                "assistant": assistant_text,
                "workspace": row.get("workspace") or "",
            })
            known_user_texts.add(user_text)
            added += 1
        if added:
            data["chat"].sort(key=lambda t: t.get("timestamp", ""))
            data["chat"] = data["chat"][-(CONVERSATION_MAX_TURNS * 2) :]
            _save(user_id, data)
        return added


def save_conversation_turn(
    user_id: str,
    user_message: str,
    assistant_message: str,
    *,
    workspace: str = "",
) -> None:
    """Append one user/assistant exchange for the next run's message history."""
    user_id = validate_user_id(user_id)
    with _user_lock(user_id):
        data = _load(user_id)
        data["chat"].append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "user": _truncate_text(user_message, CONVERSATION_USER_MAX),
            "assistant": _truncate_text(assistant_message, CONVERSATION_ASSISTANT_MAX),
            "workspace": workspace or "",
        })
        # Keep enough rows that trimming by turns/chars can still use recent history
        data["chat"] = data["chat"][-(CONVERSATION_MAX_TURNS * 2) :]
        _save(user_id, data)


def get_conversation_messages(user_id: str) -> list[dict]:
    """
    OpenAI-style message list (user/assistant only) from recent stored turns.

    Newest turns are included first until CONVERSATION_MAX_TURNS or
    CONVERSATION_MAX_CHARS is reached.
    """
    user_id = validate_user_id(user_id)
    sync_tasks_to_chat(user_id)
    data = _load(user_id)
    turns = sorted(data.get("chat") or [], key=lambda t: t.get("timestamp", ""))
    if not turns:
        return []

    messages: list[dict] = []
    total_chars = 0
    turn_count = 0

    for turn in reversed(turns):
        if turn_count >= CONVERSATION_MAX_TURNS:
            break
        user_text = (turn.get("user") or "").strip()
        assistant_text = (turn.get("assistant") or "").strip()
        if not user_text and not assistant_text:
            continue

        pair_chars = len(user_text) + len(assistant_text)
        if messages and total_chars + pair_chars > CONVERSATION_MAX_CHARS:
            break

        pair_msgs: list[dict] = []
        if user_text:
            pair_msgs.append({"role": "user", "content": user_text})
        if assistant_text:
            pair_msgs.append({"role": "assistant", "content": assistant_text})
        if not pair_msgs:
            continue

        messages = pair_msgs + messages
        total_chars += pair_chars
        turn_count += 1

    return messages


def get_conversation_turn_count(user_id: str) -> int:
    """Number of stored user/assistant turns (for UI)."""
    user_id = validate_user_id(user_id)
    return len(_load(user_id).get("chat") or [])


def clear_conversation_memory(user_id: str) -> None:
    """Remove cross-run chat history; task list and workspaces are unchanged."""
    user_id = validate_user_id(user_id)
    with _user_lock(user_id):
        data = _load(user_id)
        data["chat"] = []
        _save(user_id, data)
