"""
CLI entry point for Termai.

Commands: login, memory, skills, persona, setup, or a task string (--file for uploads).
"""

import getpass
import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent import run_agent
from auth import authenticate, cli_resolve_user, users_file_ready
from memory import get_all_tasks
from persona import ensure_persona_files, list_persona_files
from skills import list_skills
from paths import user_agent_home

console = Console()


def _parse_cli_upload(args: list[str]) -> tuple[tuple[str, bytes] | None, list[str]]:
    """Extract --file path from argv; returns (upload_tuple, remaining_args)."""
    upload = None
    rest = []
    i = 0
    while i < len(args):
        if args[i] == "--file" and i + 1 < len(args):
            path = os.path.abspath(args[i + 1])
            with open(path, "rb") as f:
                upload = (os.path.basename(path), f.read())
            i += 2
        else:
            rest.append(args[i])
            i += 1
    return upload, rest


def show_memory(user_id: str):
    """Print task history table for the memory subcommand."""
    tasks = get_all_tasks(user_id)

    if tasks:
        table = Table(title=f"Task History ({user_id})", border_style="magenta")
        table.add_column("Time", style="dim")
        table.add_column("Task", style="white")
        table.add_column("Summary", style="green")
        for t in reversed(tasks):
            table.add_row(t["timestamp"], t["task"], t.get("summary", "")[:80])
        console.print(table)
    else:
        console.print("[dim]No memory yet.[/dim]")


def cli_login() -> str:
    """Interactive username/password prompt; returns user_id."""
    if not users_file_ready():
        console.print("[red]No users.json found. Copy users.json.example to users.json.[/red]")
        sys.exit(1)
    username = console.input("[cyan]Username:[/cyan] ").strip().lower()
    password = getpass.getpass("Password: ")
    session = authenticate(username, password)
    if not session:
        console.print("[red]Invalid username or password.[/red]")
        sys.exit(1)
    return session["user_id"]


def main():
    """Parse argv, authenticate, dispatch to run_agent or subcommands."""
    args = sys.argv[1:]
    user_id, args = cli_resolve_user(args)

    if args and args[0] == "login":
        user_id = cli_login()
        args = args[1:]

    if not user_id:
        if not args:
            console.print(Panel(
                "[bold cyan]Termai Agent[/bold cyan]\n"
                "[dim]Sign in required. Use: python main.py login[/dim]\n"
                "[dim]Or: python main.py --user alice --password ... \"your task\"[/dim]",
                border_style="cyan",
            ))
            sys.exit(0)
        console.print(
            "[red]Authentication required.[/red]\n"
            "  python main.py login\n"
            "  python main.py --user alice --password secret \"task\"\n"
            "  TERMAI_PASSWORD=secret python main.py --user alice \"task\"",
        )
        sys.exit(1)

    if not args:
        console.print(Panel(
            f"[bold cyan]Termai[/bold cyan] [dim]({user_id})[/dim]\n[dim]Type your task and press Enter[/dim]",
            border_style="cyan",
        ))
        task = console.input("[bold magenta]> [/bold magenta]")
        run_agent(task, user_id=user_id)

    elif args[0] == "memory":
        show_memory(user_id)

    elif args[0] == "skills":
        skills = list_skills(user_id)
        if not skills:
            console.print("[dim]No skills found.[/dim]")
        else:
            table = Table(title="Available Skills", border_style="cyan")
            table.add_column("Id", style="cyan")
            table.add_column("Title", style="white")
            table.add_column("Source", style="dim")
            table.add_column("When to use", style="dim")
            for s in skills:
                table.add_row(
                    s["skill_id"],
                    s["title"],
                    s["source"],
                    (s.get("when_to_use") or "—")[:60],
                )
            console.print(table)

    elif args[0] == "persona":
        from auth import load_users
        display = load_users().get(user_id, {}).get("name", user_id)
        ensure_persona_files(user_id, display)
        home = user_agent_home(user_id)
        table = Table(title=f"Persona files ({user_id})", border_style="cyan")
        table.add_column("File", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Status", style="dim")
        for row in list_persona_files(user_id):
            table.add_row(
                row["file"],
                row["description"],
                "present" if row["exists"] else "missing",
            )
        console.print(table)
        console.print(f"[dim]Agent home: {home}[/dim]")
        console.print("[dim]Edit files in the Persona page (web UI) or directly on disk.[/dim]")

    elif args[0] == "setup":
        from auth import load_users
        display = load_users().get(user_id, {}).get("name", user_id)
        home = ensure_persona_files(user_id, display)
        console.print(f"[green]✓ Persona files ready at:[/green] {home}")

    else:
        upload, rest = _parse_cli_upload(args)
        task = " ".join(rest).strip() or (
            "Analyze the uploaded data file." if upload else ""
        )
        if not task:
            console.print("[red]Provide a task or --file path.[/red]")
            sys.exit(1)
        run_agent(task, user_id=user_id, upload=upload)


if __name__ == "__main__":
    main()
