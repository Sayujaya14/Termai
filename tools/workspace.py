"""Per-run task workspace boundary for file write tools."""

import contextvars
import os

_task_workspace: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "task_workspace", default=None
)


def set_task_workspace(path: str | None) -> None:
    if path is None:
        _task_workspace.set(None)
        return
    _task_workspace.set(os.path.abspath(path))


def get_task_workspace() -> str | None:
    return _task_workspace.get()


def resolve_writable_path(path: str) -> str:
    """
    Resolve path and ensure it lies inside the active task workspace.
    Raises ValueError when no workspace is set or the path escapes it.
    """
    root = get_task_workspace()
    if not root:
        raise ValueError("No task workspace is active for this write.")

    abs_path = os.path.abspath(path)
    root = os.path.abspath(root)

    if abs_path == root or abs_path.startswith(root + os.sep):
        return abs_path

    raise ValueError(
        f"Path is outside the task workspace: {path!r}. "
        f"Writes must stay under {root}/"
    )
