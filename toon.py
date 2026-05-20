"""
TOON (Token-Oriented Object Notation) serializer/deserializer.

Format spec:
  @section_name          -> starts a section
  col1|col2|col3         -> header row for tabular section
  val1|val2|val3         -> data row (no repeated keys)
  # comment              -> ignored
"""


def dumps(data: dict) -> str:
    lines = []

    # tasks section (tabular)
    if data.get("tasks"):
        lines.append("@tasks")
        headers = ["timestamp", "task", "workspace", "summary"]
        lines.append("|".join(headers))
        for t in data["tasks"]:
            row = [_escape(str(t.get(h, ""))) for h in headers]
            lines.append("|".join(row))
        lines.append("")

    return "\n".join(lines)


def _split_row(line: str) -> list[str]:
    """Split on | but not on escaped \\|."""
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line):
            buf.append(line[i : i + 2])
            i += 2
            continue
        if line[i] == "|":
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(line[i])
        i += 1
    parts.append("".join(buf))
    return [_unescape(p) for p in parts]


def loads(text: str) -> dict:
    data = {"tasks": []}
    section = None
    headers = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("@"):
            section = line[1:]
            headers = []
            continue

        if section == "tasks":
            cols = _split_row(line)
            if not headers:
                headers = cols
            elif len(cols) == len(headers):
                data["tasks"].append(dict(zip(headers, cols)))

    return data


def _escape(value: str) -> str:
    # escape pipe and newline so tabular structure stays intact
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "\\n")


def _unescape(value: str) -> str:
    return value.replace("\\n", "\n").replace("\\|", "|").replace("\\\\", "\\")
