"""
Prompt-based routing: classify user tasks before the agent runs.

Replaces keyword lists for:
  - chat-only answers vs full agent (tools + workspace)
  - whether to inject the task memory log
  - which skill guide to load (if any)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from user_llm import create_chat_completion
from skills import format_skill_catalog, load_skill_instructions


@dataclass(frozen=True)
class TaskRoute:
    """Result of classifying one user message."""

    mode: str  # "chat" | "agent"
    needs_memory_log: bool
    skill_file: str | None


ROUTING_SYSTEM = """You route user messages for Termai, a coding agent with terminal and file tools.

Reply with ONLY a JSON object (no markdown fences, no extra text):
{"mode":"chat"|"agent","needs_memory_log":true|false,"skill":null|"<skill_filename>"}

mode rules:
- "chat": definitions, explanations, greetings, conceptual Q&A, conversation recall.
  No code execution, files, terminal, datasets, or reports needed.
  Examples: "what is EDA?", "hi", "explain overfitting", "what was my last question?"
- "agent": run code, create/edit files, analyze data, build reports, scrape web,
  install packages, execute scripts, or process an uploaded file.
  Examples: "create an EDA report on iris", "fix this script", "plot sales.csv"

needs_memory_log rules:
- true only when the user asks about prior messages, their last question, earlier tasks,
  or what they asked before in this conversation.

skill rules:
- null unless mode is "agent" AND exactly one skill from the catalog clearly applies.
- Do NOT attach a skill for definition-only or conceptual questions.
  Example: "what is eda" -> mode chat, skill null.
- skill value must be an exact id from the catalog (e.g. eda_report.md or personal/weekly_kpi.md).

Skill catalog:
{catalog}
"""


def _extract_json(text: str) -> dict | None:
    """Parse JSON from model output, tolerating stray whitespace."""
    text = (text or "").strip()
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _normalize_route(data: dict | None, *, has_upload: bool, user_id: str) -> TaskRoute:
    """Validate router JSON; safe defaults when parsing fails."""
    if not isinstance(data, dict):
        default_mode = "agent" if has_upload else "chat"
        return TaskRoute(mode=default_mode, needs_memory_log=False, skill_file=None)

    mode = str(data.get("mode", "chat")).strip().lower()
    if mode not in ("chat", "agent"):
        mode = "chat"

    needs_memory = bool(data.get("needs_memory_log", False))

    skill_file = data.get("skill")
    if skill_file in (None, "null", ""):
        skill_file = None
    elif isinstance(skill_file, str) and skill_file.endswith(".md"):
        if load_skill_instructions(skill_file, user_id) is None:
            skill_file = None
    else:
        skill_file = None

    if mode == "chat":
        skill_file = None

    return TaskRoute(
        mode=mode,
        needs_memory_log=needs_memory,
        skill_file=skill_file,
    )


def classify_task(
    task: str,
    user_id: str,
    *,
    has_upload: bool = False,
) -> TaskRoute:
    """
    Use a short LLM call to decide chat vs agent, memory log, and skill.

    Uploads force agent mode but still run the classifier for skill selection.
    On classifier failure, defaults to chat (avoids accidental file creation).
    """
    catalog = format_skill_catalog(user_id) or "(none)"
    system_content = ROUTING_SYSTEM.replace("{catalog}", catalog)
    messages = [
        {
            "role": "system",
            "content": system_content,
        },
        {"role": "user", "content": task.strip()},
    ]

    try:
        response = create_chat_completion(
            user_id,
            messages=messages,
            max_tokens=120,
            temperature=0,
        )
        raw = response.choices[0].message.content or ""
        data = _extract_json(raw)
        route = _normalize_route(data, has_upload=has_upload, user_id=user_id)
    except Exception:
        route = TaskRoute(mode="chat", needs_memory_log=False, skill_file=None)

    if has_upload:
        return TaskRoute(
            mode="agent",
            needs_memory_log=route.needs_memory_log,
            skill_file=route.skill_file,
        )
    return route
