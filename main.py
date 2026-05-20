import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from agent import run_agent
from memory import get_all_tasks
from skills import list_skills

console = Console()


def show_memory():
    tasks = get_all_tasks()

    if tasks:
        table = Table(title="Task History", border_style="magenta")
        table.add_column("Time", style="dim")
        table.add_column("Task", style="white")
        table.add_column("Summary", style="green")
        for t in reversed(tasks):
            table.add_row(t["timestamp"], t["task"], t.get("summary", "")[:80])
        console.print(table)
    else:
        console.print("[dim]No memory yet.[/dim]")


def main():
    args = sys.argv[1:]

    if not args:
        console.print(Panel(
            "[bold cyan]OpenClaw-like Agent[/bold cyan]\n[dim]Type your task and press Enter[/dim]",
            border_style="cyan"
        ))
        task = console.input("[bold magenta]> [/bold magenta]")
        run_agent(task)

    elif args[0] == "memory":
        show_memory()

    elif args[0] == "skills":
        skills = list_skills()
        if not skills:
            console.print("[dim]No skills found in skills/ folder.[/dim]")
        else:
            table = Table(title="Available Skills", border_style="cyan")
            table.add_column("File", style="cyan")
            table.add_column("Title", style="white")
            table.add_column("Triggers", style="dim")
            for s in skills:
                table.add_row(s["file"], s["title"], ", ".join(s["keywords"][:4]))
            console.print(table)

    else:
        run_agent(" ".join(args))


if __name__ == "__main__":
    main()
