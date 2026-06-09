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

MODEL = os.getenv("TERMAI_MODEL", "gpt-4o").strip()
FALLBACK_MODEL = os.getenv("TERMAI_FALLBACK_MODEL", "openai/gpt-4o-mini").strip()

# Presets for per-user LLM settings (Settings page)
PROVIDER_PRESETS = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "default_fallback_model": "gpt-4o-mini",
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-4o-mini",
        "default_fallback_model": "",
    },
    "custom": {
        "label": "Custom (OpenAI-compatible)",
        "base_url": "",
        "default_model": "",
        "default_fallback_model": "",
    },
}
COMMAND_TIMEOUT = 120  # seconds for shell commands
MAX_TOKENS = 80000  # rough context budget for message trimming
# Cap completion length sent to the API (OpenRouter bills/reserves by this limit)
MAX_OUTPUT_TOKENS = int(os.getenv("TERMAI_MAX_OUTPUT_TOKENS", "4096"))

# Cross-run conversation memory (ChatGPT-style), stored in memory/<user>.toon @chat
CONVERSATION_MAX_TURNS = int(os.getenv("TERMAI_CONVERSATION_MAX_TURNS", "15"))
CONVERSATION_MAX_CHARS = int(os.getenv("TERMAI_CONVERSATION_MAX_CHARS", "24000"))
CONVERSATION_USER_MAX = 4000  # max chars stored per user message in history
CONVERSATION_ASSISTANT_MAX = 8000  # max chars stored per assistant reply in history

# Google OAuth (optional — web UI "Sign in with Google")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8501",
).strip()
NGROK_PUBLIC_URL = os.getenv("TERMAI_NGROK_URL", "").strip()
OAUTH_DYNAMIC_REDIRECT = os.getenv("TERMAI_OAUTH_DYNAMIC_REDIRECT", "false").strip().lower() in (
    "1",
    "true",
    "yes",
)
OAUTH_STATE_SECRET = (
    os.getenv("TERMAI_OAUTH_STATE_SECRET", "").strip() or GOOGLE_CLIENT_SECRET or "termai-dev"
)
_allowed = os.getenv("TERMAI_GOOGLE_ALLOWED_DOMAINS", "").strip()
GOOGLE_ALLOWED_DOMAINS = (
    {d.strip().lower() for d in _allowed.split(",") if d.strip()}
    if _allowed
    else None
)

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


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str | None = None,
) -> float:
    """Estimate USD cost for a completion using MODEL_PRICING."""
    model_name = (model or MODEL).strip()
    pricing = MODEL_PRICING.get(model_name)
    if pricing is None and "/" in model_name:
        pricing = MODEL_PRICING.get(model_name.rsplit("/", 1)[-1])
    if pricing is None:
        pricing = {"input": 0, "output": 0}
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
- For downloads use `curl -sS` or `wget -q` so progress meters don't clutter the terminal
- For EDA reports: call `report_html.build_eda_report()` for a styled self-contained HTML report (embedded base64 charts). Use pandas, matplotlib, seaborn. Never use sweetviz, pandas_profiling or ydata_profiling
- For data tasks: use pandas, matplotlib, seaborn, scikit-learn
- Be concise in your final response — just state what was done and what files were created"""
