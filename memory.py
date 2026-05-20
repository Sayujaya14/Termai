import os
from datetime import datetime
import toon

MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.toon")


def _load() -> dict:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return toon.loads(f.read())
    return {"tasks": []}


def _save(data: dict):
    with open(MEMORY_FILE, "w") as f:
        f.write(toon.dumps(data))


def save_task(task: str, workspace: str, summary: str = ""):
    data = _load()
    data["tasks"].append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "task": task,
        "workspace": workspace,
        "summary": summary
    })
    data["tasks"] = data["tasks"][-20:]
    _save(data)


def update_summary(task: str, summary: str):
    data = _load()
    for t in reversed(data["tasks"]):
        if t["task"] == task:
            t["summary"] = summary[:200]
            break
    _save(data)


def get_memory_context() -> str:
    data = _load()
    lines = []

    if data["tasks"]:
        lines.append("Previous tasks:")
        for t in data["tasks"][-5:]:
            summary = f" → {t['summary']}" if t.get("summary") else ""
            lines.append(f"  [{t['timestamp']}] {t['task']}{summary}")
            lines.append(f"    Workspace: {t['workspace']}")

    return "\n".join(lines) if lines else ""


def get_all_tasks() -> list:
    return _load()["tasks"]
