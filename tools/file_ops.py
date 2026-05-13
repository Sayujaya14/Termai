import os
import difflib
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


def read_file(path: str) -> str:
    try:
        with open(path, "r") as f:
            content = f.read()
        console.print(Panel(f"[green]Read {path}[/green] ({len(content)} chars)", border_style="green"))
        return content
    except Exception as e:
        return f"Error: {e}"


def write_file(path: str, content: str) -> str:
    try:
        abs_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        if os.path.exists(abs_path):
            with open(abs_path, "r") as f:
                old = f.readlines()
            diff = list(difflib.unified_diff(
                old, content.splitlines(keepends=True),
                fromfile=f"a/{path}", tofile=f"b/{path}", lineterm=""
            ))
            if diff:
                console.print(Panel(
                    Syntax("".join(diff[:50]), "diff", theme="monokai"),
                    title=f"[yellow]Overwriting {path}[/yellow]",
                    border_style="yellow"
                ))

        with open(abs_path, "w") as f:
            f.write(content)
        console.print(f"[green]✓ Written:[/green] {path}")
        return f"Written to {path}"
    except Exception as e:
        return f"Error: {e}"


def patch_file(path: str, old_str: str, new_str: str) -> str:
    try:
        with open(path, "r") as f:
            content = f.read()

        if old_str not in content:
            return f"Error: Could not find the target string in {path}"

        patched = content.replace(old_str, new_str, 1)

        diff = list(difflib.unified_diff(
            content.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile=f"a/{path}", tofile=f"b/{path}", lineterm=""
        ))
        if diff:
            console.print(Panel(
                Syntax("".join(diff[:50]), "diff", theme="monokai"),
                title=f"[yellow]Patching {path}[/yellow]",
                border_style="yellow"
            ))

        with open(path, "w") as f:
            f.write(patched)
        console.print(f"[green]✓ Patched:[/green] {path}")
        return f"Patched {path} successfully"
    except Exception as e:
        return f"Error: {e}"


def list_directory(path: str) -> str:
    try:
        entries = []
        for entry in sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name)):
            prefix = "📁" if entry.is_dir() else "📄"
            entries.append(f"{prefix} {entry.name}")
        result = "\n".join(entries) or "(empty)"
        console.print(Panel(result, title=f"[cyan]📂 {path}[/cyan]", border_style="cyan"))
        return result
    except Exception as e:
        return f"Error: {e}"
