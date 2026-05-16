import asyncio
from collections.abc import Iterable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from council.config import load_config
from council.models import CandidateAnswer, CouncilRun, Settings, Vote
from council.orchestrator import run_fast_council
from council.voting import top_tied_labels


console = Console()


def main() -> None:
    try:
        settings = load_config()
    except Exception as exc:
        console.print(
            Panel(
                f"Could not load config.yaml:\n{exc}",
                title="Configuration Error",
                border_style="red",
            )
        )
        raise SystemExit(1) from exc

    _render_header(settings)
    prompt = _read_prompt()
    if not prompt:
        console.print("[yellow]No prompt entered. Exiting.[/yellow]")
        raise SystemExit(1)

    with console.status("[bold]Running Fast Council...[/bold]", spinner="dots"):
        run = asyncio.run(run_fast_council(prompt, config=settings))

    _render_run(run)


def _render_header(settings: Settings) -> None:
    console.print(
        Panel.fit(
            "[bold]LLM Council[/bold]\nFast Council via local Ollama",
            border_style="cyan",
        )
    )
    console.print(f"[bold]Ollama:[/bold] {settings.ollama.base_url}")
    console.print(f"[bold]Run log:[/bold] {settings.app.runs_path}")
    console.print(_members_table(settings))


def _members_table(settings: Settings) -> Table:
    table = Table(title="Council Members", show_lines=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Model", style="green")
    table.add_column("Temp", justify="right")
    table.add_column("Role")

    for member in settings.council:
        table.add_row(
            member.name,
            member.model,
            f"{member.temperature:g}",
            member.role,
        )

    return table


def _read_prompt() -> str:
    console.print()
    console.print("[bold]Enter your prompt.[/bold]")
    console.print("[dim]Finish with an empty line.[/dim]")

    lines: list[str] = []
    while True:
        try:
            line = console.input("[cyan]> [/cyan]")
        except EOFError:
            break

        if line == "":
            break
        lines.append(line)

    return "\n".join(lines).strip()


def _render_run(run: CouncilRun) -> None:
    console.print()
    _render_errors(run.errors)
    _render_final_answer(run)
    _render_vote_summary(run)
    _render_votes(run.votes)
    _render_candidates(run.candidates)


def _render_errors(errors: Iterable[str]) -> None:
    for error in errors:
        console.print(Panel(error, title="Warning", border_style="yellow"))


def _render_final_answer(run: CouncilRun) -> None:
    if run.winner_label and run.final_answer:
        console.print(
            Panel(
                _answer_text(run.final_answer),
                title=f"Final Answer - Winner {run.winner_label}",
                border_style="green",
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

    console.print(Panel(message, title="No Single Winner", border_style="yellow"))


def _render_vote_summary(run: CouncilRun) -> None:
    if not run.vote_counts:
        return

    table = Table(title="Vote Summary")
    table.add_column("Label", style="bold cyan")
    table.add_column("Votes", justify="right")

    for label, count in run.vote_counts.items():
        table.add_row(label, str(count))

    console.print(table)


def _render_votes(votes: list[Vote]) -> None:
    if not votes:
        return

    table = Table(title="Votes", show_lines=True)
    table.add_column("Member", style="bold cyan")
    table.add_column("Model", style="green")
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
                border_style="red",
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
                border_style="blue",
            )
        )


def _answer_text(answer: str) -> Text:
    return Text(answer or "(empty response)")


if __name__ == "__main__":
    main()
