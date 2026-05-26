import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")


# =========================
# FALLBACK (OpenRouter)
# =========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1"
)

MODEL = "gpt-4o"
FALLBACK_MODEL = "openai/gpt-4o-mini"
COMMAND_TIMEOUT = 120
MAX_TOKENS = 80000


DANGEROUS_PATTERNS = [
    "rm -rf", "rm -f", "mkfs", "dd if=",
    ":(){:|:&};:", "chmod -R 777", "sudo rm", "> /dev/", "format"
]


# pricing per 1M tokens (USD) — update if model changes
MODEL_PRICING = {
    "gpt-4o":           {"input": 2.50, "output": 10.00},
    "gpt-4o-mini":      {"input": 0.15, "output": 0.60},
    "gpt-4-turbo":      {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo":    {"input": 0.50, "output": 1.50},
}


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    pricing = MODEL_PRICING.get(MODEL, {"input": 0, "output": 0})
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

SYSTEM_PROMPT = """You are an expert AI coding agent with full terminal access. You can run shell commands, read/write files, and fix errors iteratively.

Guidelines:
- All files you create MUST be inside the workspace folder provided in the task
- Always use absolute paths when writing or running files
- Prefer patch_file over write_file when modifying existing files
- Install missing dependencies automatically using pip/npm/etc
- If a command fails, read the error carefully and fix it before retrying
- For EDA reports: use pandas, matplotlib and seaborn. Never use sweetviz, pandas_profiling or ydata_profiling
- For data tasks: use pandas, matplotlib, seaborn, scikit-learn
- Be concise in your final response — just state what was done and what files were created"""


