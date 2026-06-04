"""
Skill guides: markdown files in skills/ with trigger keywords.

When a task matches keywords, the skill instructions are injected into the agent prompt.
"""

import os

SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills")


def _parse_skill(content: str) -> dict:
    """Parse SKILL.md into keywords list and instruction body (without trigger section)."""
    keywords = []
    instructions_lines = []
    in_keywords = False

    for line in content.splitlines():
        if line.strip() == "## Trigger keywords":
            in_keywords = True
            continue
        if in_keywords and line.startswith("##"):
            in_keywords = False
        if in_keywords:
            if line.strip() and not line.startswith("#"):
                keywords = [k.strip().lower() for k in line.split(",")]
        else:
            instructions_lines.append(line)

    return {
        "keywords": keywords,
        "instructions": "\n".join(instructions_lines).strip(),
    }


def find_skill(task: str) -> str | None:
    """Return skill instructions if any keyword appears in the task text."""
    if not os.path.exists(SKILLS_DIR):
        return None

    task_lower = task.lower()
    for filename in os.listdir(SKILLS_DIR):
        if not filename.endswith(".md"):
            continue
        path = os.path.join(SKILLS_DIR, filename)
        with open(path, "r") as f:
            content = f.read()
        parsed = _parse_skill(content)
        if any(kw in task_lower for kw in parsed["keywords"]):
            return parsed["instructions"]
    return None


def list_skills() -> list[dict]:
    """List all skills for the Skills page / CLI (file, title, keywords)."""
    skills = []
    if not os.path.exists(SKILLS_DIR):
        return skills
    for filename in sorted(os.listdir(SKILLS_DIR)):
        if not filename.endswith(".md"):
            continue
        path = os.path.join(SKILLS_DIR, filename)
        with open(path, "r") as f:
            content = f.read()
        title = content.splitlines()[0].replace("# Skill: ", "").strip()
        keywords = _parse_skill(content)["keywords"]
        skills.append({"file": filename, "title": title, "keywords": keywords})
    return skills
