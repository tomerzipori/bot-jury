import asyncio
from pathlib import Path

from council.config import DEFAULT_CONFIG_PATH, load_config
from council.models import CandidateAnswer, CouncilMember, CouncilRun, Settings, Vote
from council.ollama_client import OllamaClient
from council.prompts import build_answer_messages, build_vote_messages
from council.storage import append_run
from council.utils import label_for_index
from council.voting import count_votes, determine_winner, parse_vote


async def run_fast_council(
    prompt: str,
    config: Settings | None = None,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> CouncilRun:
    settings = config or load_config(config_path)
    client = OllamaClient(
        settings.ollama.base_url,
        timeout_seconds=settings.ollama.request_timeout_seconds,
    )
    errors: list[str] = []

    answer_results = await asyncio.gather(
        *[_request_answer(client, member, prompt) for member in settings.council],
        return_exceptions=True,
    )

    candidates: list[CandidateAnswer] = []
    successful_members: list[CouncilMember] = []
    for member, result in zip(settings.council, answer_results):
        if isinstance(result, Exception):
            errors.append(_format_model_error(member, result))
            continue

        label = label_for_index(len(candidates))
        candidates.append(
            CandidateAnswer(
                label=label,
                member_name=member.name,
                model=member.model,
                answer=result,
            )
        )
        successful_members.append(member)

    labels = [candidate.label for candidate in candidates]
    if len(candidates) < 2:
        if len(candidates) == 1:
            errors.append(
                "Only one model returned an answer. "
                "At least two are required for council voting."
            )
        else:
            errors.append(
                "No models returned answers. At least two are required for council voting."
            )

        run = CouncilRun(
            prompt=prompt,
            candidates=candidates,
            votes=[],
            vote_counts={label: 0 for label in labels},
            winner_label=None,
            final_answer=None,
            errors=errors,
        )
        _save_run(settings.app.runs_path, run)
        return run

    labeled_answers = {candidate.label: candidate.answer for candidate in candidates}
    vote_results = await asyncio.gather(
        *[
            _request_vote(client, member, prompt, labeled_answers)
            for member in successful_members
        ],
        return_exceptions=True,
    )

    votes: list[Vote] = []
    for member, result in zip(successful_members, vote_results):
        if isinstance(result, Exception):
            error = _format_model_error(member, result)
            errors.append(error)
            votes.append(
                Vote(
                    member_name=member.name,
                    model=member.model,
                    valid=False,
                    error=error,
                )
            )
            continue

        votes.append(result)

    vote_counts = count_votes(votes, labels)
    winner_label = determine_winner(vote_counts)
    final_answer = _answer_for_label(candidates, winner_label) if winner_label else None

    run = CouncilRun(
        prompt=prompt,
        candidates=candidates,
        votes=votes,
        vote_counts=vote_counts,
        winner_label=winner_label,
        final_answer=final_answer,
        errors=errors,
    )
    _save_run(settings.app.runs_path, run)
    return run


async def _request_answer(
    client: OllamaClient,
    member: CouncilMember,
    prompt: str,
) -> str:
    return await client.chat(
        model=member.model,
        messages=build_answer_messages(member.role, prompt),
        temperature=member.temperature,
    )


async def _request_vote(
    client: OllamaClient,
    member: CouncilMember,
    prompt: str,
    labeled_answers: dict[str, str],
) -> Vote:
    raw_response = await client.chat(
        model=member.model,
        messages=build_vote_messages(member.role, prompt, labeled_answers),
        temperature=member.temperature,
    )
    vote, reason, valid, error = parse_vote(raw_response, set(labeled_answers))
    return Vote(
        member_name=member.name,
        model=member.model,
        vote=vote,
        reason=reason,
        raw_response=raw_response,
        valid=valid,
        error=error,
    )


def _answer_for_label(candidates: list[CandidateAnswer], label: str | None) -> str | None:
    if label is None:
        return None

    for candidate in candidates:
        if candidate.label == label:
            return candidate.answer
    return None


def _format_model_error(member: CouncilMember, error: Exception) -> str:
    return (
        f"Model {member.model} failed for {member.name}. "
        f"Check that it is pulled in Ollama. Details: {error}"
    )


def _save_run(path: str, run: CouncilRun) -> None:
    try:
        append_run(path, run)
    except OSError as exc:
        run.errors.append(f"Failed to save run to {path}: {exc}")
