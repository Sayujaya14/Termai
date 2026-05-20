import json
import os
import re
from datetime import datetime
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from config import MODEL, MAX_TOKENS, SYSTEM_PROMPT, API_KEY, BASE_URL, calculate_cost
from tools import TOOLS, handle_tool
from memory import get_memory_context, save_task, update_summary
from paths import make_task_workspace
from skills import find_skill

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
console = Console()


def get_project_context(cwd: str) -> str:
    lines = [f"Working directory: {cwd}"]
    try:
        for entry in sorted(os.scandir(cwd), key=lambda e: e.name):
            if entry.name.startswith("."):
                continue
            lines.append(f"  {entry.name}{'/' if entry.is_dir() else ''}")
    except Exception:
        pass
    return "\n".join(lines)


def get_role(m) -> str:
    return m.get("role") if isinstance(m, dict) else m.role


def trim_messages(messages: list) -> list:
    system = [m for m in messages if get_role(m) == "system"]
    rest = [m for m in messages if get_role(m) != "system"]
    total = sum(len(str(m)) for m in rest)
    while total > MAX_TOKENS * 4 and len(rest) > 2:
        rest.pop(0)
        total = sum(len(str(m)) for m in rest)
    return system + rest


SIMPLE_QUERY_PATTERNS = [
    r'^what\b', r'^who\b', r'^why\b', r'^how\b', r'^when\b', r'^where\b',
    r'^explain\b', r'^define\b', r'^tell me\b', r'^describe\b',
    r'^what is\b', r'^what are\b', r'^can you explain\b', r'^difference between\b',
    r'^which\b', r'^is\b', r'^are\b', r'^does\b', r'^do\b', r'^can\b',
    r'^give me an example\b', r'^show me an example\b',
]

GREETINGS = ["hi", "hello", "hey", "hii", "helo", "yo"]
ACTION_KEYWORDS = [
    "create", "build", "make", "generate", "write", "run", "execute", "install",
    "scrape", "train", "deploy", "fix", "debug", "analyze", "plot", "download",
    "fetch", "send", "eda", "report", "dataset", "csv", "script", "code",
]


def is_simple_query(task: str) -> bool:
    t = task.strip().lower()
    # strip leading greeting words like "hi", "hello", "hey"
    for greet in GREETINGS:
        if t.startswith(greet + " "):
            t = t[len(greet):].strip()
            break
    if any(kw in t for kw in ACTION_KEYWORDS):
        return False
    return any(re.match(p, t) for p in SIMPLE_QUERY_PATTERNS)


def _chat_memory_label() -> str:
    return f"(chat/{datetime.now().strftime('%Y%m%d_%H%M%S')})"


def answer_directly(task: str, user_id: str, callback=None):
    """Answer simple questions without workspace, tools or file creation."""
    memory_label = _chat_memory_label()
    save_task(user_id, task, memory_label)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Answer the question concisely in plain text. Do NOT create any files, do NOT use any tools, do NOT write code unless explicitly asked."},
            {"role": "user", "content": task}
        ]
        # no tools passed — so LLM physically cannot call any
    )
    answer = response.choices[0].message.content or ""
    input_tokens = response.usage.prompt_tokens if response.usage else 0
    output_tokens = response.usage.completion_tokens if response.usage else 0
    cost = calculate_cost(input_tokens, output_tokens)
    cost_str = f"${cost:.4f}" if cost >= 0.0001 else "< $0.0001"
    usage_str = f"🪙 {input_tokens + output_tokens} tokens ({input_tokens} in / {output_tokens} out) — {cost_str}"

    summary = f"{(answer or '')[:180]} | {usage_str}"
    update_summary(user_id, memory_label, summary)

    if callback:
        callback("thinking", "💾 Saved to memory (chat only — no workspace files)")
        callback("done", answer)
        callback("cost", usage_str)
    console.print(Panel(f"[bold green]{answer}[/bold green]\n[dim]{usage_str}[/dim]",
                        title="[bold green]✅ Answer[/bold green]", border_style="green"))


def run_agent(task: str, user_id: str, callback=None):
    if is_simple_query(task):
        console.print(f"[dim]💬 Simple query — answering directly[/dim]")
        if callback:
            callback("thinking", "💬 Simple query — answering directly")
        answer_directly(task, user_id, callback)
        return

    workspace = make_task_workspace(user_id, task)
    console.print(f"[dim]📂 Workspace: {workspace}[/dim]")
    if callback:
        callback("thinking", f"Workspace: {workspace}")

    memory_ctx = get_memory_context(user_id)
    memory_section = f"\n\nMemory (past tasks):\n{memory_ctx}" if memory_ctx else ""

    skill = find_skill(task)
    skill_section = f"\n\nRelevant skill guide:\n{skill}" if skill else ""
    if skill:
        console.print(f"[dim]📖 Skill matched for this task[/dim]")
        if callback:
            callback("skill", "📖 Skill matched for this task")

    save_task(user_id, task, workspace)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Workspace folder: {workspace}\nAll scripts AND output files must be saved inside: {workspace}\nAlways use absolute paths starting with {workspace}/{memory_section}{skill_section}\n\nTask: {task}"}
    ]

    console.print(Panel(
        f"[bold white]{task}[/bold white]",
        title="[bold magenta]🤖 Agent Task[/bold magenta]",
        border_style="magenta"
    ))

    step = 0
    total_input_tokens = 0
    total_output_tokens = 0

    while True:
        step += 1
        messages = trim_messages(messages)

        if callback:
            callback("thinking", f"Thinking... (step {step})")

        with console.status(f"[bold cyan]Thinking... (step {step})[/bold cyan]", spinner="dots"):
            response = client.chat.completions.create(
                model=MODEL,
                tools=TOOLS,
                messages=messages
            )

        # accumulate token usage
        if response.usage:
            total_input_tokens += response.usage.prompt_tokens
            total_output_tokens += response.usage.completion_tokens

        message = response.choices[0].message
        messages.append(message)
        finish = response.choices[0].finish_reason

        if finish == "stop":
            summary = message.content or ""
            cost = calculate_cost(total_input_tokens, total_output_tokens)
            cost_str = f"${cost:.4f}" if cost >= 0.0001 else "< $0.0001"
            usage_str = f"🪙 {total_input_tokens + total_output_tokens} tokens ({total_input_tokens} in / {total_output_tokens} out) — {cost_str}"

            update_summary(user_id, workspace, f"{summary[:180]} | {usage_str}")
            if callback:
                callback("done", message.content)
                callback("cost", usage_str)
            console.print(Panel(
                f"[bold green]{message.content}[/bold green]\n[dim]{usage_str}[/dim]",
                title="[bold green]✅ Done[/bold green]",
                border_style="green"
            ))
            break

        if finish == "tool_calls":
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                inputs = json.loads(tool_call.function.arguments)
                console.print(f"\n[bold cyan]🔧 Tool:[/bold cyan] [yellow]{name}[/yellow]")
                if callback:
                    callback("tool", f"{name}: {json.dumps(inputs)[:200]}")
                result = handle_tool(name, inputs, callback=callback)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
