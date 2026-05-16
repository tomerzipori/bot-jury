# Bot Jury

Bot Jury is a local CLI that asks several Ollama-powered bots to answer the same prompt, makes them vote on the best answer, and shows you the winning response.

It is built for quick local decision-making: write a prompt, let the bots judge the options, then run another prompt without restarting the terminal.

## What It Does

- Sends your prompt to five configured council members.
- Collects independent candidate answers.
- Anonymizes the answers before voting.
- Asks the successful bots to vote for the best answer.
- Prints the winning final answer first.
- Optionally shows the vote summary, each vote, and candidate answers.
- Saves every run to `runs.jsonl`.

Bot Jury runs locally through Ollama. It does not call hosted AI APIs.

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com)
- The configured local model, currently `nemotron-3-nano:4b`

## Quick Start

Install Ollama first, then run:

```bash
./install.sh
```

The installer creates a `.venv`, installs Python dependencies, pulls the default Ollama model, and creates a local launcher named `llm-council`.

Start the app:

```bash
./llm-council
```

## Usage

At startup, choose an action:

```text
Enter  Run council
c      Configure
q      Quit
```

Press Enter to run the jury, type your prompt, and press Enter again.

After the final answer is printed, you can choose whether to show voting details and candidate answers. When a run finishes, Bot Jury returns to the action menu so you can run another prompt, configure the council, or quit.

## Configuration

The default council is defined in `config.yaml`.

Each member has:

- `name`: display name in vote details.
- `model`: local Ollama model name.
- `role`: instruction that shapes how the member answers and votes.
- `temperature`: model temperature for answer and vote calls.

Use `c` in the CLI to edit the existing members. The editor changes member names, models, roles, and temperatures, then saves back to `config.yaml`.

## Ollama

Make sure Ollama is running before starting Bot Jury. By default, the app calls:

```text
http://localhost:11434/api/chat
```

If the configured model is missing, install it with:

```bash
ollama pull nemotron-3-nano:4b
```

You can use a different local model by editing `config.yaml` or using the built-in configuration flow.

## Development

Set up the environment manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Run checks:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

## Notes

- This version implements a single Fast Council workflow.
- At least two successful candidate answers are required for voting.
- Runs are appended as JSON lines to the path configured by `app.runs_path`.
