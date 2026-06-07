# Termai

An AI coding agent with full terminal access. Give it a task — it writes code, runs it, fixes errors, and delivers output files.

## Features
- 🖥️ Terminal execution with live streaming output
- 🔒 Safety confirmation before dangerous commands
- 📁 Isolated workspace per user and task
- 👤 Multi-user auth (username/password, per-user memory)
- 🔑 Per-user API key, provider, and model (Settings page)
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

Copy the example env file and set your credentials:

```bash
cp .env.example .env
```

Required in `.env`:

```bash
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
TERMAI_MODEL=gpt-4o
TERMAI_FALLBACK_MODEL=openai/gpt-4o-mini
```

Create user accounts:

```bash
cp users.json.example users.json
```

Default demo users (password for both: `password123`):

| Username | Display name |
|----------|----------------|
| `alice`  | Alice          |
| `bob`    | Bob            |

Generate a new password hash:

```bash
python auth.py hash-password your-secret
```

## Usage

### Web UI

```bash
streamlit run app.py
```

Open the URL shown (e.g. `http://localhost:8501`), sign in, then run tasks.

**Settings** (sidebar): each user can save a personal API key, provider (OpenAI, OpenRouter, or custom OpenAI-compatible endpoint), and model. If no personal key is set, Termai uses server defaults from `.env`.

When a task creates files in your workspace, a **Download outputs (.zip)** button appears on the Agent page after it finishes.

Production / LAN binding:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Use HTTPS and a firewall in real deployments — each user still shares the same server shell.

### CLI

```bash
# interactive login, then task
python main.py login

# one-shot with credentials
python main.py --user alice --password password123 "create an eda report on iris"

# or password via env
TERMAI_PASSWORD=password123 python main.py --user bob memory
python main.py --user alice skills
```

## Project Structure

```
Termai/
├── app.py              # Streamlit UI (login + agent)
├── main.py             # CLI entry point
├── agent.py            # agent loop
├── auth.py             # users.json auth (bcrypt)
├── user_llm.py         # per-user LLM provider, key, model
├── config.py           # model, API key, system prompt
├── memory.py           # per-user persistent memory
├── toon.py             # TOON serializer
├── skills.py           # skill matching & loading
├── users.json.example  # template user accounts
├── memory/             # per-user *.toon (gitignored), e.g. memory/alice.toon
├── workspaces/         # workspaces/<user>/<task>_<time>/ (gitignored)
├── paths.py            # per-user workspace paths
├── tools/
│   ├── __init__.py
│   ├── executor.py
│   └── file_ops.py
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

## Security notes

- Personal API keys are stored in `users.json` on the server (plaintext). Restrict file permissions and do not commit `users.json`.
- Users are isolated by **memory file** and **workspace folder**, not by OS sandbox.
- Shell commands run on the host as the Streamlit/CLI process user.
- Do not expose to the public internet without extra hardening (containers, VPN, rate limits).
