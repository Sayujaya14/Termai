"""
Restrict file writes to the active task workspace for the current agent run.

Uses a context variable set by handle_tool() so write_file/patch_file cannot
escape to persona files or other users' folders.
"""

import contextvars
import os

_task_workspace: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "task_workspace", default=None
)


def set_task_workspace(path: str | None) -> None:
    """Set the allowed root for write_file/patch_file (None disables enforcement)."""
    if path is None:
        _task_workspace.set(None)
        return
    _task_workspace.set(os.path.abspath(path))


def get_task_workspace() -> str | None:
    """Return the current task workspace root, if any."""
    return _task_workspace.get()


def resolve_writable_path(path: str) -> str:
    """
    Resolve path and ensure it is inside the active task workspace.

    Relative paths are resolved against the workspace root (not process cwd).

    Raises ValueError if no workspace is set or the path escapes the root.
    """
    root = get_task_workspace()
    if not root:
        raise ValueError("No task workspace is active for this write.")

    root = os.path.abspath(root)
    if os.path.isabs(path):
        abs_path = os.path.abspath(path)
    else:
        abs_path = os.path.abspath(os.path.join(root, path))

    if abs_path == root or abs_path.startswith(root + os.sep):
        return abs_path

    raise ValueError(
        f"Path is outside the task workspace: {path!r}. "
        f"Writes must stay under the active task workspace."
    )
