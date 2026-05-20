# Termai

An AI coding agent with full terminal access. Give it a task — it writes code, runs it, fixes errors, and delivers output files.

## Features
- 🖥️ Terminal execution with live streaming output
- 🔒 Safety confirmation before dangerous commands
- 📁 Isolated workspace per task
- 🧠 Persistent memory across sessions (TOON format)
- 📖 Skill guides for common tasks (EDA, forecasting, scraping)
- 🔧 Diff-based file patching

## Setup

```bash
git clone <repo-url>
cd Termai
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set your OpenAI API key and base URL in `config.py`:
```python
API_KEY = "your-api-key"
BASE_URL = "your-base-url"  # or https://api.openai.com/v1
```

## Usage

```bash
# run a task
python main.py "create a eda report on iris dataset"

# interactive mode
python main.py

# view task history
python main.py memory

# list available skills
python main.py skills
```

## Project Structure

```
Termai/
├── main.py          # entry point & CLI
├── agent.py         # agent loop
├── config.py        # model, API key, system prompt
├── memory.py        # persistent memory
├── toon.py          # TOON serializer (compact format for LLM context)
├── skills.py        # skill matching & loading
├── tools/
│   ├── __init__.py  # tool schemas & dispatcher
│   ├── executor.py  # run_command (streaming + safety)
│   └── file_ops.py  # read/write/patch/list
└── skills/
    ├── eda_report.md
    ├── forecasting.md
    └── web_scraping.md
```

## Adding a Skill

Create a `.md` file in `skills/` folder:

```markdown
# Skill: My Skill

## Trigger keywords
keyword1, keyword2, keyword3

## Steps
1. ...

## Rules
- ...
```
