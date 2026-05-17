import asyncio
from collections.abc import Iterable

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from council.config import load_config, resolve_config_path, save_config
from council.models import (
    CandidateAnswer,
    CouncilMember,
    CouncilRun,
    ScoreReview,
    Settings,
    Vote,
)
from council.ollama_client import OllamaClient
from council.orchestrator import run_fast_council
from council.voting import top_tied_labels


APP_THEME = Theme(
    {
        "brand": "#ff9aa2 bold",
        "accent": "#ff9aa2",
        "muted": "grey50",
        "success": "green3",
        "warning": "#ff9aa2",
        "danger": "red3",
        "border": "grey50",
    }
)
console = Console(theme=APP_THEME)
PREFLIGHT_TIMEOUT_SECONDS = 5
COUNCIL_STATUS_INTERVAL_SECONDS = 4
COUNCIL_STATUS_MESSAGES = [
    "Waking up the council...",
    "Passing notes between tiny geniuses...",
    "Collecting suspiciously confident answers...",
    "Scoring candidate answers...",
    "Checking the review rubric...",
    "Polishing the least-wrong answer...",
]


def main(
    config_path: str | None = None,
    *,
    stream: bool | None = None,
) -> None:
    try:
        _main(config_path=config_path, stream=stream)
    except KeyboardInterrupt:
        console.print("\n[warning]Cancelled.[/warning]")
        raise SystemExit(130) from None
    except Exception as exc:
        console.print(
            Panel(
                str(exc),
                title="Unexpected Error",
                border_style="danger",
            )
        )
        raise SystemExit(1) from exc


def _main(
    config_path: str | None = None,
    *,
    stream: bool | None = None,
) -> None:
    resolved_config_path = resolve_config_path(config_path)
    try:
        settings = load_config(resolved_config_path)
    except Exception as exc:
        console.print(
            Panel(
                f"Could not load {resolved_config_path}:\n{exc}",
                title="Configuration Error",
                border_style="danger",
            )
        )
        raise SystemExit(1) from exc

    while True:
        _render_header(settings)
        action = _read_start_action()
        if action == "q":
            console.print("[muted]Goodbye.[/muted]")
            return
        if action == "c":
            settings = _configure_settings(settings, resolved_config_path)
            continue
        _run_council(settings, stream=stream)


def _run_council(
    settings: Settings,
    *,
    stream: bool | None = None,
) -> None:
    prompt = _read_prompt()
    if not prompt:
        console.print("[warning]No prompt entered. Exiting.[/warning]")
        raise SystemExit(1)

    with console.status("[accent]Checking Ollama...[/accent]", spinner="dots"):
        preflight_errors = asyncio.run(_preflight_ollama(settings))
    if preflight_errors:
        _render_errors(preflight_errors)
        raise SystemExit(1)

    run = asyncio.run(_run_council_with_status(prompt, settings, stream=stream))

    _render_run(run)


def _render_header(settings: Settings) -> None:
    console.print(
        Panel.fit(
            "[brand]Bot Jury[/brand]\n"
            "[muted]Make them decide for you.[/muted]",
            border_style="border",
            padding=(1, 2),
        )
    )
    console.print(f"[accent]Run log:[/accent] {settings.app.runs_path}")


def _members_table(settings: Settings) -> Table:
    table = Table(
        title="Council Members",
        show_lines=True,
        header_style="accent",
        border_style="border",
    )
    table.add_column("Name", style="accent")
    table.add_column("Model", style="muted")
    table.add_column("Temp", justify="right", style="muted")
    table.add_column("Role", style="grey70")

    for member in settings.council:
        table.add_row(
            member.name,
            member.model,
            f"{member.temperature:g}",
            member.role,
        )

    return table


def _read_start_action() -> str:
    console.print()
    console.print(_actions_menu())

    while True:
        try:
            action = console.input("[accent]Action> [/accent]").strip().lower()
        except EOFError:
            return "q"

        if action in {"", "c", "q"}:
            return action
        console.print("[warning]Choose Enter, c, or q.[/warning]")


def _actions_menu() -> Panel:
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="accent")
    grid.add_column(style="muted")
    grid.add_row("Enter", "Run council")
    grid.add_row("c", "Configure")
    grid.add_row("q", "Quit")
    return Panel.fit(grid, title="Actions", border_style="border", padding=(0, 1))


def _read_prompt() -> str:
    console.print()
    console.print("[brand]Enter your prompt.[/brand]")
    try:
        return console.input("[accent]> [/accent]").strip()
    except EOFError:
        return ""


def _configure_settings(settings: Settings, config_path: str | None = None) -> Settings:
    edited = settings.model_copy(deep=True)
    console.print(
        Panel(
            "Edit the existing council members. Press Enter to keep a value.",
            title="Configure Council",
            border_style="border",
        )
    )

    for index, member in enumerate(edited.council, start=1):
        console.print(
            Panel(
                _member_summary(member),
                title=f"Member {index}",
                border_style="border",
            )
        )
        member.name = _read_required_value("Name", member.name)
        member.model = _read_required_value("Model", member.model)
        member.role = _read_required_value("Instruction", member.role)
        member.temperature = _read_temperature(member.temperature)

    console.print()
    console.print(_members_table(edited))
    target_path = resolve_config_path(config_path)
    if not _confirm(f"Save changes to {target_path}?"):
        console.print("[muted]Configuration unchanged.[/muted]")
        return settings

    save_config(edited, target_path)
    console.print(f"[success]Saved {target_path}.[/success]")
    return edited


def _member_summary(member: CouncilMember) -> str:
    return (
        f"[accent]Name:[/accent] {escape(member.name)}\n"
        f"[accent]Model:[/accent] {escape(member.model)}\n"
        f"[accent]Temperature:[/accent] {member.temperature:g}\n"
        f"[accent]Instruction:[/accent] {escape(member.role)}"
    )


def _read_required_value(label: str, current: str) -> str:
    while True:
        try:
            value = console.input(
                f"[accent]{label}[/accent] (current: {escape(current)}): "
            ).strip()
        except EOFError:
            return current

        value = value or current
        if value:
            return value
        console.print(f"[warning]{label} cannot be empty.[/warning]")


def _read_temperature(current: float) -> float:
    while True:
        try:
            value = console.input(
                f"[accent]Temperature[/accent] (current: {current:g}): "
            ).strip()
        except EOFError:
            return current

        if not value:
            return current
        try:
            return float(value)
        except ValueError:
            console.print("[warning]Temperature must be a number.[/warning]")


def _confirm(prompt: str) -> bool:
    try:
        answer = console.input(f"{escape(prompt)} \\[y/N] ")
    except EOFError:
        return False
    return answer.strip().lower() in {"y", "yes"}


async def _preflight_ollama(settings: Settings) -> list[str]:
    client = OllamaClient(
        settings.ollama.base_url,
        timeout_seconds=PREFLIGHT_TIMEOUT_SECONDS,
    )
    try:
        installed_models = await client.list_models()
    except Exception as exc:
        return [str(exc)]

    required_models = {member.model for member in settings.council}
    missing_models = sorted(required_models - installed_models)
    if not missing_models:
        return []

    pulls = "\n".join(f"ollama pull {model}" for model in missing_models)
    return [
        "Missing required Ollama model(s): "
        f"{', '.join(missing_models)}\n\nInstall them with:\n{pulls}"
    ]


async def _run_council_with_status(
    prompt: str,
    settings: Settings,
    *,
    stream: bool | None = None,
) -> CouncilRun:
    should_stream = stream if stream is not None else settings.ollama.max_parallel_requests == 1
    should_stream = bool(should_stream and settings.ollama.max_parallel_requests == 1)
    if should_stream:
        _render_candidate_chunk._active = set()  # type: ignore[attr-defined]
        console.print("[accent]Streaming candidate answers...[/accent]")
        run = await run_fast_council(
            prompt,
            config=settings,
            stream_candidates=True,
            on_candidate_chunk=_render_candidate_chunk,
        )
        console.print()
        return run

    task = asyncio.create_task(run_fast_council(prompt, config=settings))
    message_index = 0

    with console.status(
        f"[accent]{COUNCIL_STATUS_MESSAGES[message_index]}[/accent]",
        spinner="dots",
    ) as status:
        while not task.done():
            try:
                return await asyncio.wait_for(
                    asyncio.shield(task),
                    timeout=COUNCIL_STATUS_INTERVAL_SECONDS,
                )
            except TimeoutError:
                message_index = (message_index + 1) % len(COUNCIL_STATUS_MESSAGES)
                status.update(
                    f"[accent]{COUNCIL_STATUS_MESSAGES[message_index]}[/accent]"
                )

        return await task


def _render_candidate_chunk(member: CouncilMember, chunk: str) -> None:
    if not chunk:
        return

    key = (member.name, member.model)
    if not hasattr(_render_candidate_chunk, "_active"):
        _render_candidate_chunk._active = set()  # type: ignore[attr-defined]

    active = _render_candidate_chunk._active  # type: ignore[attr-defined]
    if key not in active:
        console.print()
        console.print(
            Panel.fit(
                f"{escape(member.name)} / {escape(member.model)}",
                title="Candidate",
                border_style="border",
            )
        )
        active.add(key)

    console.print(Text(chunk), end="")


def _render_run(run: CouncilRun) -> None:
    console.print()
    _render_errors(run.errors)
    _render_final_answer(run)
    if _has_details(run) and _wants_details():
        _render_details(run)


def _render_details(run: CouncilRun) -> None:
    _render_score_summary(run)
    _render_score_reviews(run.score_reviews)
    _render_vote_summary(run)
    _render_votes(run.votes)
    _render_candidates(run.candidates)


def _has_details(run: CouncilRun) -> bool:
    return bool(
        run.score_totals
        or run.score_reviews
        or run.vote_counts
        or run.votes
        or run.candidates
    )


def _wants_details() -> bool:
    console.print()
    try:
        answer = console.input(
            "Show scoring details and candidate answers? \\[y/N] "
        )
    except EOFError:
        return False
    return answer.strip().lower() in {"y", "yes"}


def _render_errors(errors: Iterable[str]) -> None:
    for error in errors:
        console.print(Panel(error, title="Warning", border_style="warning"))


def _render_final_answer(run: CouncilRun) -> None:
    if run.winner_label and run.final_answer:
        console.print(
            Panel(
                _answer_text(run.final_answer),
                title=f"Final Answer - Winner {run.winner_label}",
                border_style="success",
            )
        )
        return

    tied = top_tied_labels(run.vote_counts)
    if tied:
        message = f"No single winner. Tied answers: {', '.join(tied)}"
    elif run.candidates:
        message = "No single winner. No valid votes were recorded."
    else:
        message = "No candidate answers are available."

    console.print(Panel(message, title="No Single Winner", border_style="warning"))


def _render_vote_summary(run: CouncilRun) -> None:
    if not run.vote_counts:
        return

    table = Table(title="Vote Summary", header_style="accent", border_style="border")
    table.add_column("Label", style="accent")
    table.add_column("Votes", justify="right")

    for label, count in run.vote_counts.items():
        table.add_row(label, str(count))

    console.print(table)


def _render_score_summary(run: CouncilRun) -> None:
    if not run.score_totals:
        return

    table = Table(title="Score Summary", header_style="accent", border_style="border")
    table.add_column("Label", style="accent")
    table.add_column("Weighted Score", justify="right")

    for label, score in sorted(
        run.score_totals.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        table.add_row(label, f"{score:.2f}")

    console.print(table)


def _render_score_reviews(reviews: list[ScoreReview]) -> None:
    if not reviews:
        return

    table = Table(
        title="Score Reviews",
        show_lines=True,
        header_style="accent",
        border_style="border",
    )
    table.add_column("Member", style="accent")
    table.add_column("Model", style="muted")
    table.add_column("Best", justify="center")
    table.add_column("Valid", justify="center")
    table.add_column("Scores")
    table.add_column("Error")

    for review in reviews:
        scores = "\n".join(
            (
                f"{score.label}: c{score.correctness} "
                f"cmp{score.completeness} cl{score.clarity} "
                f"u{score.usefulness} s{score.safety}"
            )
            for score in review.scores
        )
        table.add_row(
            review.member_name,
            review.model,
            review.best_label or "-",
            "yes" if review.valid else "no",
            scores,
            review.error or "",
        )

    console.print(table)


def _render_votes(votes: list[Vote]) -> None:
    if not votes:
        return

    table = Table(
        title="Votes",
        show_lines=True,
        header_style="accent",
        border_style="border",
    )
    table.add_column("Member", style="accent")
    table.add_column("Model", style="muted")
    table.add_column("Vote", justify="center")
    table.add_column("Valid", justify="center")
    table.add_column("Reason")
    table.add_column("Error")

    for vote in votes:
        table.add_row(
            vote.member_name,
            vote.model,
            vote.vote or "-",
            "yes" if vote.valid else "no",
            vote.reason,
            vote.error or "",
        )

    console.print(table)

    invalid_votes = [vote for vote in votes if not vote.valid and vote.raw_response]
    for vote in invalid_votes:
        console.print(
            Panel(
                vote.raw_response,
                title=f"Invalid Raw Vote - {vote.member_name} / {vote.model}",
                border_style="danger",
            )
        )


def _render_candidates(candidates: list[CandidateAnswer]) -> None:
    if not candidates:
        return

    for candidate in candidates:
        console.print(
            Panel(
                _answer_text(candidate.answer),
                title=(
                    f"Candidate {candidate.label} - "
                    f"{candidate.member_name} / {candidate.model}"
                ),
                border_style="border",
            )
        )


def _answer_text(answer: str) -> Text:
    return Text(answer or "(empty response)")


if __name__ == "__main__":
    main()
