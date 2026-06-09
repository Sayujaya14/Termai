"""
Skill guides: markdown files in skills/ loaded when the prompt router selects one.

Skills are chosen by an LLM routing step (task_router.py), not keyword matching.
"""

import os

SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills")


def _parse_skill(content: str) -> dict:
    """Parse a skill markdown file into metadata and instruction body."""
    title = ""
    when_to_use = ""
    instructions_lines = []
    in_when = False

    for line in content.splitlines():
        if line.startswith("# Skill:"):
            title = line.replace("# Skill:", "").strip()
            continue
        stripped = line.strip()
        if stripped in ("## When to use", "## Trigger keywords"):
            in_when = True
            continue
        if in_when and line.startswith("##"):
            in_when = False
        if in_when:
            if stripped and not stripped.startswith("#"):
                when_to_use = stripped if not when_to_use else f"{when_to_use} {stripped}"
        else:
            instructions_lines.append(line)

    return {
        "title": title,
        "when_to_use": when_to_use.strip(),
        "instructions": "\n".join(instructions_lines).strip(),
    }


def _iter_skill_files() -> list[str]:
    if not os.path.exists(SKILLS_DIR):
        return []
    return sorted(
        f for f in os.listdir(SKILLS_DIR) if f.endswith(".md")
    )


def load_skill_instructions(filename: str) -> str | None:
    """Return skill instructions for a catalog filename, or None if missing."""
    if not filename or not filename.endswith(".md"):
        return None
    path = os.path.join(SKILLS_DIR, filename)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        parsed = _parse_skill(f.read())
    return parsed["instructions"] or None


def format_skill_catalog() -> str:
    """One-line-per-skill summary for the routing prompt."""
    lines = []
    for filename in _iter_skill_files():
        path = os.path.join(SKILLS_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            parsed = _parse_skill(f.read())
        title = parsed["title"] or filename
        when = parsed["when_to_use"] or "See skill file."
        lines.append(f"- {filename}: {title} — {when}")
    return "\n".join(lines)


def list_skills() -> list[dict]:
    """List all skills for the Skills page / CLI."""
    skills = []
    for filename in _iter_skill_files():
        path = os.path.join(SKILLS_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            parsed = _parse_skill(f.read())
        skills.append({
            "file": filename,
            "title": parsed["title"] or filename,
            "when_to_use": parsed["when_to_use"],
        })
    return skills
