"""Save user-uploaded CSV/XLSX into the task workspace."""

import os
import re

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def save_upload(workspace: str, filename: str, data: bytes) -> str:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type {ext!r}. Use CSV or XLSX.")

    safe = re.sub(r"[^\w.\-]", "_", os.path.basename(filename)) or f"upload{ext}"
    path = os.path.join(workspace, safe)
    with open(path, "wb") as f:
        f.write(data)
    return os.path.abspath(path)


def upload_prompt_section(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    reader = "pd.read_csv" if ext == ".csv" else "pd.read_excel (pip install openpyxl if needed)"
    return (
        f"\n\nUploaded data file: {path}\n"
        f"Load with pandas: {reader}(r'{path}')\n"
        "Use this file as the dataset for the task."
    )
