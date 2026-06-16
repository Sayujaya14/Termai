# Termai

An AI coding agent with full terminal access, delivered as both a Streamlit web app and a CLI. Give it a task in plain language — it routes the request, writes and runs code in an isolated workspace, fixes its own errors, and hands back the output files.

## Features

- 🖥️ **Terminal execution** with live-streamed output and self-correcting retries
- 🧭 **Prompt-based router** — a short LLM classifier decides *chat* (answer directly) vs *agent* (tools + workspace), and picks a matching skill guide
- 🧰 **Five tools** — `run_command`, `read_file`, `write_file`, `patch_file` (diff-based edits), `list_directory`
- 📁 **Isolated workspace** per user and per task (`workspaces/<user>/<task>_<time>/`)
- 👤 **Multi-user auth** — username/password (bcrypt) and optional Google sign-in
- 🔑 **Per-user LLM settings** — provider, API key, model, fallback, and output-token cap (Settings page), with server `.env` defaults as a fallback
- 🔒 **API keys encrypted at rest** in `users.json` (see [Security](#security))
- 🧠 **Persistent memory** — task history plus ChatGPT-style conversation recall across runs (TOON format)
- 🪪 **Persona / bootstrap files** per user (AGENTS.md, SOUL.md, USER.md, …) injected into the system prompt
- 📊 **One-call reports** — styled self-contained EDA report and time-series ARIMA forecast report (HTML + CSV)
- 📖 **Skill guides** for common tasks (EDA, forecasting, web scraping) plus per-user personal skills
- 🎨 **Light / dark theme toggle**, saved per user
- 💰 **Token & cost tracking** shown after every run
- 📦 **Download outputs** as a `.zip` when a task produces files

## Architecture at a glance

```
task ──▶ task_router.classify_task()
            │  chat?  ──▶ answer_directly()      (no tools, no files)
            └─ agent? ──▶ run_agent()            (workspace + tools loop)
                              │
                              ├─ persona system prompt (build_system_prompt)
                              ├─ memory context + conversation history
                              ├─ optional skill guide + uploaded file
                              └─ LLM ⇄ tools loop until "stop"
                                       run_command / read / write / patch / list
```

The same `run_agent()` powers both the web UI ([app.py](app.py)) and the CLI ([main.py](main.py)).

## Setup

```bash
git clone <repo-url>
cd Termai
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy and edit the environment file:

```bash
cp .env.example .env
```

Minimum required in `.env`:

```bash
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
TERMAI_MODEL=openai/gpt-5.1
TERMAI_FALLBACK_MODEL=openai/gpt-4o-mini
TERMAI_MAX_OUTPUT_TOKENS=4096
```

> These are the **server defaults**. Any user who saves a personal key in Settings overrides them for their own runs.

Create user accounts:

```bash
cp users.json.example users.json
```

Default demo users (password for both: `password123`):

| Username | Display name |
|----------|--------------|
| `alice`  | Alice        |
| `bob`    | Bob          |

Generate a fresh password hash for a new user:

```bash
python auth.py hash-password your-secret
```

### Optional: Google sign-in (web UI)

Create OAuth credentials in the Google Cloud Console, then set in `.env`:

```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8501
# TERMAI_GOOGLE_ALLOWED_DOMAINS=yourcompany.com   # restrict to a domain
```

Add the redirect URI **exactly** (no trailing slash) under "Authorized redirect URIs", and open the app at that same URL. If `GOOGLE_CLIENT_ID`/`SECRET` are unset, the Google button is disabled and only username/password is used.

### Optional: fallback provider & secret key

```bash
# OpenRouter as a fallback LLM endpoint
OPENROUTER_API_KEY=sk-or-v1-your-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Encryption key for secrets at rest (auto-created as .termai_key if unset)
TERMAI_SECRET_KEY=base64-fernet-key
```

## Usage

### Web UI

```bash
streamlit run app.py
```

Open the URL shown (e.g. `http://localhost:8501`), sign in, then work from the sidebar pages:

- **Agent** — describe a task and run it; watch the terminal stream live. A **Download outputs (.zip)** button appears after a task creates files.
- **Persona** — edit your bootstrap files (identity, rules, user info) that shape the agent.
- **Memory** — browse your task history.
- **Skills** — view built-in skill guides (read-only) and create/manage your own.
- **Settings** — save a personal provider (OpenAI / OpenRouter / custom OpenAI-compatible), API key, model, fallback model, and max output tokens. Leave blank to use server `.env` defaults.

The **theme toggle** (light/dark) lives in the sidebar and is remembered per user.

LAN / production binding:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Use HTTPS and a firewall in real deployments — all users still share the same host shell (see [Security](#security)).

### CLI

```bash
# interactive login, then prompt for a task
python main.py login

# one-shot with credentials
python main.py --user alice --password password123 "create an eda report on iris"

# password via environment variable
TERMAI_PASSWORD=password123 python main.py --user bob "forecast sales.csv for 12 months"

# subcommands
python main.py --user alice memory     # task history
python main.py --user alice skills     # available skill guides
python main.py --user alice persona    # persona file status
python main.py --user alice setup      # seed persona files

# attach a file to a task
python main.py --user alice --file data.csv "analyze this dataset"
```

## Project structure

```
Termai/
├── app.py                # Streamlit web UI (login, sidebar pages, agent terminal)
├── main.py               # CLI entry point (login, task, subcommands)
├── agent.py              # core agent loop (LLM ⇄ tools) + chat-only path
├── task_router.py        # prompt-based chat/agent + skill routing
├── auth.py               # users.json auth (bcrypt), session handling
├── google_auth.py        # Google OAuth sign-in flow
├── user_llm.py           # per-user LLM settings + theme; client + completion calls
├── secrets_crypto.py     # symmetric encryption-at-rest for API keys
├── config.py             # env config, system prompt, danger patterns, pricing
├── persona.py            # OpenClaw-style persona/bootstrap files → system prompt
├── memory.py             # per-user task + conversation memory (TOON)
├── toon.py               # TOON serializer/parser
├── skills.py             # skill catalog matching & loading
├── report_html.py        # EDA + ARIMA forecast HTML report builders
├── paths.py              # per-user agent home & task workspace paths
├── uploads.py            # save uploaded files into a workspace
├── workspace_zip.py      # zip a task workspace for download
├── ui_styles.py          # shared theme CSS (light/dark palettes) + helpers
├── ui_attach.py          # file-attach widget for the agent input bar
├── tools/
│   ├── __init__.py       # TOOLS schema + handle_tool dispatcher
│   ├── executor.py       # run_command (streamed, with safety checks)
│   ├── file_ops.py       # read/write/patch/list files
│   └── workspace.py      # task-workspace sandbox context
├── templates/
│   ├── persona/          # AGENTS, SOUL, USER, IDENTITY, BOOTSTRAP, TOOLS, HEARTBEAT
│   └── reports/          # eda_report.html/.css, forecast_report.html
├── skills/               # built-in skill guides (eda_report, forecasting, web_scraping)
├── .streamlit/config.toml# Streamlit theme base
├── users.json.example    # template user accounts
├── memory/               # per-user *.toon (gitignored)
└── workspaces/           # per-user/per-task run folders (gitignored)
```

## Reports

The agent is instructed to use helpers in [report_html.py](report_html.py) for two common deliverables:

- **EDA report** — `build_eda_report()` produces a styled, self-contained HTML file with embedded base64 charts and summary statistics (pandas / matplotlib / seaborn).
- **Forecast report** — `build_forecast_report()` produces a time-series ARIMA forecast as HTML plus `forecast.csv`. It needs a date column and a numeric target (auto-detected if not specified).

## Adding a skill

Built-in skills live in `skills/`; personal skills are created per user from the Skills page. A skill is a Markdown guide the prompt router can attach to an agent run — the `## When to use` line is what the router matches against (there are no keyword lists):

```markdown
# Skill: My Skill

## When to use
A one-line description of exactly when this skill applies.

## Steps
1. ...
2. ...
```

## Security

- **API keys are encrypted at rest.** Personal keys are stored as ciphertext in `users.json` using a Fernet key from `TERMAI_SECRET_KEY` or an auto-created, gitignored `.termai_key`. This keeps keys out of plaintext on disk (accidental commits, backups, stray reads yield ciphertext). It does **not** protect against a process that can read the server's own key — that requires execution sandboxing.
- **The dangerous-command blocklist is a speed bump, not a sandbox.** `DANGEROUS_PATTERNS` in [config.py](config.py) catches common destructive commands (`rm -rf`, `mkfs`, `dd of=/dev/…`, fork bombs, `sudo`, …), but a determined caller can evade any blocklist.
- **Users are isolated by memory file and workspace folder, not by OS sandbox.** Shell commands run on the host as the Streamlit/CLI process user, and all users share that shell.
- **Do not expose to the public internet without hardening** — run behind HTTPS, a firewall/VPN, per-container isolation, and rate limits. Never commit `users.json`, `.env`, or `.termai_key`.

## License

See [LICENSE](LICENSE).
