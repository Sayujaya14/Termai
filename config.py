"""
Application configuration loaded from environment variables (.env).

Holds API keys, model names, timeouts, the default system prompt,
dangerous-command patterns, and token cost estimation.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Primary LLM API (OpenAI-compatible endpoint)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# Fallback LLM API when primary fails or is not configured
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1",
)

MODEL = "gpt-4o"
FALLBACK_MODEL = "openai/gpt-4o-mini"
COMMAND_TIMEOUT = 120  # seconds for shell commands
MAX_TOKENS = 80000  # rough context budget for message trimming

# Substrings that trigger safety checks in run_command
DANGEROUS_PATTERNS = [
    "rm -rf", "rm -f", "mkfs", "dd if=",
    ":(){:|:&};:", "chmod -R 777", "sudo rm", "> /dev/", "format",
]

# Pricing per 1M tokens (USD) — used for display only
MODEL_PRICING = {
    "gpt-4o":           {"input": 2.50, "output": 10.00},
    "gpt-4o-mini":      {"input": 0.15, "output": 0.60},
    "gpt-4-turbo":      {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo":    {"input": 0.50, "output": 1.50},
}


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost for a completion using MODEL_PRICING."""
    pricing = MODEL_PRICING.get(MODEL, {"input": 0, "output": 0})
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000


# Base instructions for the coding agent (persona files are appended separately)
SYSTEM_PROMPT = """You are an expert AI coding agent with full terminal access. You can run shell commands, read/write files, and fix errors iteratively.

The Project Context section below contains your workspace bootstrap files (AGENTS.md, SOUL.md, USER.md, etc.). Follow them for persona, boundaries, and operating rules.

Runtime guidelines:
- All task output files MUST be inside the task workspace folder provided in the user message
- Persona and memory files (AGENTS.md, SOUL.md, MEMORY.md, memory/*.md) live in the agent home folder
- Always use absolute paths when writing or running files
- Prefer patch_file over write_file when modifying existing files
- Install missing dependencies automatically using pip/npm/etc
- If a command fails, read the error carefully and fix it before retrying
- For EDA reports: use pandas, matplotlib and seaborn. Never use sweetviz, pandas_profiling or ydata_profiling
- For data tasks: use pandas, matplotlib, seaborn, scikit-learn
- Be concise in your final response — just state what was done and what files were created"""
