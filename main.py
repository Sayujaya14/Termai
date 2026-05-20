import getpass
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent import run_agent
from auth import authenticate, cli_resolve_user, users_file_ready
from memory import get_all_tasks
from skills import list_skills

console = Console()


def show_memory(user_id: str):
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
        run_agent(" ".join(args), user_id=user_id)


if __name__ == "__main__":
    main()
