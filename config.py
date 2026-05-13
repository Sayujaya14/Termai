import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL")

DANGEROUS_PATTERNS = [
    "rm -rf", "rm -f", "mkfs", "dd if=",
    ":(){:|:&};:", "chmod -R 777", "sudo rm", "> /dev/", "format"
]

MODEL = "gpt-4o"
COMMAND_TIMEOUT = 120
MAX_TOKENS = 80000

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
