import subprocess
import os
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Confirm
from rich.live import Live
from rich.text import Text
from config import DANGEROUS_PATTERNS, COMMAND_TIMEOUT

console = Console()


def is_dangerous(command: str) -> bool:
    return any(p in command for p in DANGEROUS_PATTERNS)


def run_command(command: str, cwd: str = None, callback=None) -> str:
    work_dir = cwd or os.getcwd()

    if is_dangerous(command):
        console.print(Panel(
            f"[bold red]⚠ DANGEROUS COMMAND DETECTED[/bold red]\n[yellow]{command}[/yellow]",
            border_style="red"
        ))
        if not Confirm.ask("[red]Are you sure you want to run this?[/red]"):
            return "Command cancelled by user."

    console.print(Panel(
        Syntax(command, "bash", theme="monokai"),
        title="[bold cyan]$ Running[/bold cyan]",
        border_style="cyan"
    ))

    output_lines = []
    try:
        process = subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=work_dir, bufsize=1
        )

        with Live(console=console, refresh_per_second=10) as live:
            for line in iter(process.stdout.readline, ""):
                for part in line.replace("\r", "\n").split("\n"):
                    part = part.strip()
                    if part:
                        output_lines.append(part)
                        if callback:
                            callback("output", part)
                display = "\n".join(output_lines[-20:])
                live.update(Panel(Text(display), title="[green]Output[/green]", border_style="green"))

        process.wait(timeout=COMMAND_TIMEOUT)
        return "\n".join(output_lines).strip() or "(no output)"

    except subprocess.TimeoutExpired:
        process.kill()
        return f"Error: Command timed out after {COMMAND_TIMEOUT} seconds"
    except Exception as e:
        return f"Error: {e}"
