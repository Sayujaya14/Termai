"""
Skill guides: built-in (repo skills/) and per-user personal (workspaces/<user>/skills/).

Personal skills use the router id prefix ``personal/`` (Option A), e.g.
``personal/weekly_kpi.md`` → ``workspaces/alice/skills/weekly_kpi.md``.
Built-in skills stay read-only in the repo ``skills/`` folder.
"""

from __future__ import annotations

import os
import re

from paths import user_skills_dir

SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills")
PERSONAL_PREFIX = "personal/"
SKILL_BASENAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,40}\.md$")
MAX_PERSONAL_SKILLS = 20
MAX_SKILL_BYTES = 32 * 1024


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

    body = "\n".join(instructions_lines).strip()
    return {
        "title": title,
        "when_to_use": when_to_use.strip(),
        "instructions": body,
        "body": body,
    }


def _iter_builtin_files() -> list[str]:
    if not os.path.exists(SKILLS_DIR):
        return []
    return sorted(f for f in os.listdir(SKILLS_DIR) if f.endswith(".md"))


def _iter_personal_files(user_id: str) -> list[str]:
    directory = user_skills_dir(user_id)
    if not os.path.isdir(directory):
        return []
    return sorted(f for f in os.listdir(directory) if f.endswith(".md"))


def personal_skill_id(basename: str) -> str:
    """Build router/catalog id for a personal skill file."""
    return f"{PERSONAL_PREFIX}{basename}"


def validate_skill_basename(filename: str) -> str:
    """Validate personal skill filename; raises ValueError if invalid."""
    name = (filename or "").strip().lower()
    if name.startswith(PERSONAL_PREFIX):
        name = name[len(PERSONAL_PREFIX) :]
    if not SKILL_BASENAME_RE.match(name):
        raise ValueError(
            "Filename must be lowercase letters, numbers, underscores, "
            "start with a letter, and end with .md (e.g. weekly_kpi.md)."
        )
    return name


def slugify_skill_filename(title: str) -> str:
    """Derive a safe personal skill filename from a title."""
    slug = re.sub(r"[^a-z0-9]+", "_", (title or "").lower()).strip("_")[:40]
    return f"{slug or 'skill'}.md"


def resolve_skill(skill_id: str, user_id: str | None) -> tuple[str, str] | None:
    """
    Resolve catalog id to (kind, path).

    kind is ``builtin`` or ``personal``; path is absolute file path.
    """
    if not skill_id or not skill_id.endswith(".md"):
        return None

    if skill_id.startswith(PERSONAL_PREFIX):
        if not user_id:
            return None
        basename = skill_id[len(PERSONAL_PREFIX) :]
        if not SKILL_BASENAME_RE.match(basename):
            return None
        path = os.path.join(user_skills_dir(user_id), basename)
        if os.path.isfile(path):
            return "personal", path
        return None

    if SKILL_BASENAME_RE.match(skill_id):
        path = os.path.join(SKILLS_DIR, skill_id)
        if os.path.isfile(path):
            return "builtin", path
    return None


def read_skill_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_skill_instructions(skill_id: str, user_id: str | None = None) -> str | None:
    """Return skill instruction body for a built-in or personal catalog id."""
    resolved = resolve_skill(skill_id, user_id)
    if not resolved:
        return None
    _, path = resolved
    parsed = _parse_skill(read_skill_file(path))
    return parsed["instructions"] or None


def list_builtin_skills() -> list[dict]:
    """Built-in repo skills (read-only for users)."""
    skills = []
    for filename in _iter_builtin_files():
        path = os.path.join(SKILLS_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            parsed = _parse_skill(f.read())
        skills.append({
            "file": filename,
            "skill_id": filename,
            "title": parsed["title"] or filename,
            "when_to_use": parsed["when_to_use"],
            "source": "built-in",
        })
    return skills


def list_personal_skills(user_id: str) -> list[dict]:
    """Personal skills for one user."""
    skills = []
    for filename in _iter_personal_files(user_id):
        path = os.path.join(user_skills_dir(user_id), filename)
        with open(path, "r", encoding="utf-8") as f:
            parsed = _parse_skill(f.read())
        skills.append({
            "file": filename,
            "skill_id": personal_skill_id(filename),
            "title": parsed["title"] or filename,
            "when_to_use": parsed["when_to_use"],
            "source": "personal",
        })
    return skills


def list_skills(user_id: str | None = None) -> list[dict]:
    """Built-in skills plus personal skills when user_id is given."""
    skills = list_builtin_skills()
    if user_id:
        skills.extend(list_personal_skills(user_id))
    return skills


def format_skill_catalog(user_id: str | None = None) -> str:
    """One-line-per-skill summary for the routing prompt."""
    lines = []
    for item in list_builtin_skills():
        when = item["when_to_use"] or "See skill file."
        lines.append(f"- {item['skill_id']}: {item['title']} — {when}")
    if user_id:
        for item in list_personal_skills(user_id):
            when = item["when_to_use"] or "See skill file."
            lines.append(f"- {item['skill_id']}: {item['title']} — {when}")
    return "\n".join(lines)


def build_skill_markdown(title: str, when_to_use: str, steps_and_rules: str) -> str:
    """Build a skill markdown document from form fields."""
    title = (title or "").strip()
    when_to_use = (when_to_use or "").strip()
    steps_and_rules = (steps_and_rules or "").strip()
    if not title:
        raise ValueError("Title is required.")
    if not when_to_use:
        raise ValueError("When to use is required.")

    parts = [
        f"# Skill: {title}",
        "",
        "## When to use",
        when_to_use,
        "",
    ]
    if steps_and_rules:
        if steps_and_rules.lstrip().startswith("#"):
            parts.append(steps_and_rules)
        else:
            parts.extend(["## Steps", steps_and_rules, ""])
    return "\n".join(parts).rstrip() + "\n"


def parse_skill_for_edit(content: str) -> dict:
    """Extract form fields from skill markdown."""
    parsed = _parse_skill(content)
    body = parsed["body"]
    if body.startswith("## Steps"):
        body = body[len("## Steps") :].lstrip("\n")
    return {
        "title": parsed["title"],
        "when_to_use": parsed["when_to_use"],
        "steps_and_rules": body,
    }


def save_personal_skill(user_id: str, filename: str, content: str) -> str:
    """Write or update a personal skill. Returns skill_id (personal/…)."""
    from paths import validate_user_id

    user_id = validate_user_id(user_id)
    basename = validate_skill_basename(filename)
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_SKILL_BYTES:
        raise ValueError(f"Skill file exceeds {MAX_SKILL_BYTES // 1024} KB limit.")

    directory = user_skills_dir(user_id)
    path = os.path.join(directory, basename)
    is_new = not os.path.isfile(path)
    if is_new and len(_iter_personal_files(user_id)) >= MAX_PERSONAL_SKILLS:
        raise ValueError(f"Maximum {MAX_PERSONAL_SKILLS} personal skills allowed.")

    _parse_skill(content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return personal_skill_id(basename)


def delete_personal_skill(user_id: str, filename: str) -> None:
    """Delete a personal skill (never touches built-in skills)."""
    from paths import validate_user_id

    user_id = validate_user_id(user_id)
    basename = validate_skill_basename(filename)
    path = os.path.join(user_skills_dir(user_id), basename)
    if not os.path.isfile(path):
        raise ValueError(f"Personal skill not found: {basename}")
    os.remove(path)


def copy_builtin_to_personal(user_id: str, builtin_filename: str) -> str:
    """Copy a built-in skill into the user's personal folder for editing."""
    from paths import validate_user_id

    user_id = validate_user_id(user_id)
    builtin_filename = validate_skill_basename(builtin_filename)
    src = os.path.join(SKILLS_DIR, builtin_filename)
    if not os.path.isfile(src):
        raise ValueError(f"Built-in skill not found: {builtin_filename}")

    content = read_skill_file(src)
    stem = builtin_filename[:-3]
    dest_name = f"{stem}_copy.md"
    existing = set(_iter_personal_files(user_id))
    n = 2
    while dest_name in existing:
        dest_name = f"{stem}_copy_{n}.md"
        n += 1
    return save_personal_skill(user_id, dest_name, content)


def read_skill_content(skill_id: str, user_id: str | None = None) -> str | None:
    """Full markdown content for UI preview."""
    resolved = resolve_skill(skill_id, user_id)
    if not resolved:
        return None
    _, path = resolved
    return read_skill_file(path)
