"""
TOON (Token-Oriented Object Notation) serializer/deserializer.

Format spec:
  @section_name          -> starts a section
  key=value              -> key-value pair (preferences)
  col1|col2|col3         -> header row for tabular section
  val1|val2|val3         -> data row (no repeated keys)
  # comment              -> ignored
"""


def dumps(data: dict) -> str:
    lines = []

    # preferences section (key=value)
    if data.get("preferences"):
        lines.append("@preferences")
        for k, v in data["preferences"].items():
            lines.append(f"{k}={_escape(str(v))}")
        lines.append("")

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


def loads(text: str) -> dict:
    data = {"preferences": {}, "tasks": []}
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

        if section == "preferences":
            if "=" in line:
                k, _, v = line.partition("=")
                data["preferences"][k.strip()] = _unescape(v.strip())

        elif section == "tasks":
            cols = [_unescape(c) for c in line.split("|")]
            if not headers:
                headers = cols
            else:
                if len(cols) == len(headers):
                    data["tasks"].append(dict(zip(headers, cols)))

    return data


def _escape(value: str) -> str:
    # escape pipe and newline so tabular structure stays intact
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "\\n")


def _unescape(value: str) -> str:
    return value.replace("\\n", "\n").replace("\\|", "|").replace("\\\\", "\\")
