# LLM Council

LLM Council is a local interactive CLI that runs a Fast Council workflow with Ollama models.

## Install

```bash
./install.sh
```

The installer creates the Python environment, installs dependencies, pulls the configured Ollama model, and creates a local `llm-council` launcher.

## Install And Run Ollama

Install Ollama from https://ollama.com before running `./install.sh`.

The installer pulls the configured model:

```bash
ollama pull nemotron-3-nano:4b
```

Make sure Ollama is running locally. The app calls:

```text
http://localhost:11434/api/chat
```

## Run App

```bash
./llm-council
```

Enter your prompt when asked and press Enter to submit.

By default, the app prints only the final answer. After the answer, you can choose whether to show voting details and candidate answers.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Notes

- All model calls are local through Ollama.
- This version implements Fast Council only.
- The five council members are configured in `config.yaml`.
- All default council members use `nemotron-3-nano:4b`.
- Each run is appended to `runs.jsonl`.
- If a configured model is unavailable, the app records the failure and continues with the successful models.
