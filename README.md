# LLM Council

LLM Council is a local interactive CLI that runs a Fast Council workflow with Ollama models.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

## Install And Run Ollama

Install Ollama from https://ollama.com, then pull the configured model:

```bash
ollama pull nemotron-3-nano:4b
```

Make sure Ollama is running locally. The app calls:

```text
http://localhost:11434/api/chat
```

## Run App

```bash
python app.py
```

Enter your prompt when asked. Finish the prompt with an empty line.

## Notes

- All model calls are local through Ollama.
- This version implements Fast Council only.
- The five council members are configured in `config.yaml`.
- All default council members use `nemotron-3-nano:4b`.
- Each run is appended to `runs.jsonl`.
- If a configured model is unavailable, the app records the failure and continues with the successful models.
