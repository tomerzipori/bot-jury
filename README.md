# Bot Jury

Bot Jury is a local CLI that asks several Ollama-powered bots to answer the
same prompt, scores the candidate answers with a reviewer rubric, and shows the
winning response.

It runs locally through Ollama. It does not call hosted AI APIs.

## What It Does

- Sends your prompt to configured council members.
- Collects independent candidate answers.
- Anonymizes answers before review.
- Scores each eligible answer for correctness, completeness, clarity,
  usefulness, and safety.
- Falls back to the older vote-counting flow if structured scoring fails.
- Prints the winning final answer first.
- Optionally shows score details, fallback votes, and candidate answers.
- Saves every run to the configured `runs.jsonl` path.

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com)
- The configured local model, currently `nemotron-3-nano:4b`

## Install

Install Ollama first, then set up the Python package:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
ollama pull nemotron-3-nano:4b
```

Start the interactive app:

```bash
bot-jury
```

## Usage

Interactive mode:

```bash
bot-jury
```

Scriptable one-shot mode:

```bash
bot-jury ask "Compare these two implementation options..."
bot-jury ask --details "What are the risks in this migration?"
bot-jury ask --json "Give me a concise release checklist."
```

Other commands:

```bash
bot-jury --help
bot-jury models list
bot-jury config path
bot-jury config show
```

Candidate streaming is available only when `ollama.max_parallel_requests` is
`1`, which keeps terminal output readable:

```bash
bot-jury --stream
bot-jury ask --stream "Draft a rollback plan."
```

## Configuration

The repo `config.yaml` is the default template. At runtime, Bot Jury copies it
to a user config path on first run:

- macOS: `~/Library/Application Support/bot-jury/config.yaml`
- Linux: `~/.config/bot-jury/config.yaml`
- Windows: `%APPDATA%\bot-jury\config.yaml`

Override the config path with an environment variable:

```bash
BOT_JURY_CONFIG=/path/to/config.yaml bot-jury ask "..."
```

Or pass an explicit path:

```bash
bot-jury --config /path/to/config.yaml config show
```

Key config fields:

- `ollama.base_url`: Ollama host URL.
- `ollama.request_timeout_seconds`: request timeout.
- `ollama.max_parallel_requests`: shared concurrency limit for model calls.
- `app.runs_path`: JSONL run history path.
- `council`: reviewer names, models, roles, and answer temperatures.

## Development

Run checks:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

Install or refresh the editable environment:

```bash
.venv/bin/python -m pip install -e ".[dev]"
```

## Notes

- At least two successful candidate answers are required for review.
- Reviewers do not score or vote for their own candidate answer.
- Runs are appended as JSON lines to the path configured by `app.runs_path`.
