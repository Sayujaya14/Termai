"""
Shell command execution for the run_command tool.

Streams output to console/UI and blocks dangerous patterns from config.
"""

import subprocess
import os
import re
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Confirm
from rich.live import Live
from rich.text import Text
from config import DANGEROUS_PATTERNS, COMMAND_TIMEOUT
from tools.workspace import get_task_workspace

console = Console()

_CURL_PROGRESS_RE = re.compile(
    r"^\s*(% Total|Dload\s+Upload|\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+[\d:]+\s+--:--:--)"
)


def _is_curl_progress_line(line: str) -> bool:
    """True for curl's stderr progress meter (merged into stdout in run_command)."""
    return bool(_CURL_PROGRESS_RE.match(line.strip()))


def is_dangerous(command: str) -> bool:
    """True if command contains any DANGEROUS_PATTERNS substring."""
    return any(p in command for p in DANGEROUS_PATTERNS)


def run_command(command: str, cwd: str = None, callback=None) -> str:
    """
    Run a shell command; return combined stdout/stderr text.

    Web UI blocks dangerous commands; CLI may prompt for confirmation.
    """
    work_dir = cwd or get_task_workspace() or os.getcwd()

    if is_dangerous(command):
        console.print(Panel(
            f"[bold red]⚠ DANGEROUS COMMAND DETECTED[/bold red]\n[yellow]{command}[/yellow]",
            border_style="red"
        ))
        if callback:
            callback("error", f"Blocked dangerous command: {command}")
            return "Command cancelled: dangerous command blocked in web UI."
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
                    if part and not _is_curl_progress_line(part):
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
