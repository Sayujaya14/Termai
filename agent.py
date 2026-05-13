import json
import os
import re
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from config import MODEL, MAX_TOKENS, SYSTEM_PROMPT, API_KEY, BASE_URL
from tools import TOOLS, handle_tool
from memory import get_memory_context, save_task, update_summary
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


def make_workspace(task: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '_', task.lower()).strip('_')[:50]
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspaces", slug)
    os.makedirs(folder, exist_ok=True)
    return folder


def run_agent(task: str):
    workspace = make_workspace(task)
    console.print(f"[dim]📂 Workspace: {workspace}[/dim]")

    memory_ctx = get_memory_context()
    memory_section = f"\n\nMemory (past tasks & preferences):\n{memory_ctx}" if memory_ctx else ""

    skill = find_skill(task)
    skill_section = f"\n\nRelevant skill guide:\n{skill}" if skill else ""
    if skill:
        console.print(f"[dim]📖 Skill matched for this task[/dim]")

    save_task(task, workspace)

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
    while True:
        step += 1
        messages = trim_messages(messages)

        with console.status(f"[bold cyan]Thinking... (step {step})[/bold cyan]", spinner="dots"):
            response = client.chat.completions.create(
                model=MODEL,
                tools=TOOLS,
                messages=messages
            )

        message = response.choices[0].message
        messages.append(message)
        finish = response.choices[0].finish_reason

        if finish == "stop":
            summary = message.content or ""
            update_summary(task, summary[:200])
            console.print(Panel(
                f"[bold green]{message.content}[/bold green]",
                title="[bold green]✅ Done[/bold green]",
                border_style="green"
            ))
            break

        if finish == "tool_calls":
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                inputs = json.loads(tool_call.function.arguments)
                console.print(f"\n[bold cyan]🔧 Tool:[/bold cyan] [yellow]{name}[/yellow]")
                result = handle_tool(name, inputs)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
