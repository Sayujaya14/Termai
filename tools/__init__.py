from tools.executor import run_command
from tools.file_ops import read_file, write_file, patch_file, list_directory

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command in the terminal and stream its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run"},
                    "cwd": {"type": "string", "description": "Working directory (optional)"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (creates or overwrites)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Full content to write"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "patch_file",
            "description": "Edit specific lines in an existing file using old/new string replacement. Prefer this over write_file for modifying existing files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to patch"},
                    "old_str": {"type": "string", "description": "Exact string to find and replace"},
                    "new_str": {"type": "string", "description": "Replacement string"}
                },
                "required": ["path", "old_str", "new_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories in a path",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list"}
                },
                "required": ["path"]
            }
        }
    }
]

TOOL_MAP = {
    "run_command": run_command,
    "read_file": read_file,
    "write_file": write_file,
    "patch_file": patch_file,
    "list_directory": list_directory,
}


def handle_tool(name: str, inputs: dict) -> str:
    fn = TOOL_MAP.get(name)
    if fn:
        return fn(**inputs)
    return f"Unknown tool: {name}"
