"""Zip task workspace folders for download."""

import io
import os
import zipfile


def zip_workspace(workspace_path: str) -> tuple[bytes, str] | None:
    """
    Zip all files under workspace_path.
    Returns (zip_bytes, filename) or None if folder missing/empty.
    """
    workspace_path = os.path.abspath(workspace_path)
    if not os.path.isdir(workspace_path):
        return None

    files: list[str] = []
    for root, _, filenames in os.walk(workspace_path):
        for name in filenames:
            full = os.path.join(root, name)
            if os.path.isfile(full):
                files.append(full)

    if not files:
        return None

    folder_name = os.path.basename(workspace_path.rstrip(os.sep)) or "outputs"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for full in files:
            arcname = os.path.join(folder_name, os.path.relpath(full, workspace_path))
            zf.write(full, arcname)

    return buf.getvalue(), f"{folder_name}.zip"
