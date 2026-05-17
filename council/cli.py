from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from pathlib import Path

import yaml

import app as interactive_app
from council.config import load_config, resolve_config_path
from council.ollama_client import OllamaClient
from council.orchestrator import run_fast_council


def app(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "ask":
        _ask(args)
        return

    if args.command == "models":
        _models(args)
        return

    if args.command == "config":
        _config(args)
        return

    interactive_app.main(
        config_path=args.config,
        stream=None if args.stream is None else args.stream,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bot-jury",
        description="Run a local Ollama-powered council of models.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config.yaml. Overrides BOT_JURY_CONFIG and the user config path.",
    )
    parser.set_defaults(command=None, stream=None)

    subparsers = parser.add_subparsers(dest="command")

    ask = subparsers.add_parser("ask", help="Run one prompt and exit.")
    ask.add_argument("prompt", help="Prompt to send to the council.")
    ask.add_argument("--details", action="store_true", help="Print scoring details.")
    ask.add_argument("--json", action="store_true", help="Print the full run as JSON.")
    ask.add_argument(
        "--stream",
        dest="stream",
        action="store_true",
        help="Stream candidate output when max_parallel_requests is 1.",
    )
    ask.add_argument(
        "--no-stream",
        dest="stream",
        action="store_false",
        help="Disable candidate streaming.",
    )
    ask.set_defaults(stream=False)

    models = subparsers.add_parser("models", help="Inspect local Ollama models.")
    models_subparsers = models.add_subparsers(dest="models_command", required=True)
    models_subparsers.add_parser("list", help="List installed Ollama models.")

    config = subparsers.add_parser("config", help="Inspect Bot Jury configuration.")
    config_subparsers = config.add_subparsers(dest="config_command", required=True)
    config_subparsers.add_parser("path", help="Print the resolved config path.")
    config_subparsers.add_parser("show", help="Print the loaded config YAML.")

    parser.add_argument(
        "--stream",
        dest="stream",
        action="store_true",
        help="Stream candidate output in interactive mode when max_parallel_requests is 1.",
    )
    parser.add_argument(
        "--no-stream",
        dest="stream",
        action="store_false",
        help="Disable interactive candidate streaming.",
    )

    return parser


def _ask(args: argparse.Namespace) -> None:
    settings = load_config(args.config)
    should_stream = bool(args.stream and settings.ollama.max_parallel_requests == 1)
    if should_stream:
        interactive_app._render_candidate_chunk._active = set()  # type: ignore[attr-defined]
    run = asyncio.run(
        run_fast_council(
            args.prompt,
            config=settings,
            stream_candidates=should_stream,
            on_candidate_chunk=interactive_app._render_candidate_chunk
            if should_stream
            else None,
        )
    )

    if args.json:
        interactive_app.console.print(run.model_dump_json())
        return

    interactive_app._render_errors(run.errors)
    interactive_app._render_final_answer(run)
    if args.details:
        interactive_app._render_details(run)


def _models(args: argparse.Namespace) -> None:
    settings = load_config(args.config)
    client = OllamaClient(
        settings.ollama.base_url,
        timeout_seconds=settings.ollama.request_timeout_seconds,
    )
    models = asyncio.run(client.list_models())
    for model in sorted(models):
        interactive_app.console.print(model)


def _config(args: argparse.Namespace) -> None:
    path = resolve_config_path(args.config)
    if args.config_command == "path":
        interactive_app.console.print(str(path))
        return

    settings = load_config(path)
    interactive_app.console.print(
        yaml.safe_dump(
            settings.model_dump(mode="json"),
            sort_keys=False,
            allow_unicode=True,
        ).rstrip()
    )
