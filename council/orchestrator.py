import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

from council.config import load_config
from council.models import (
    CandidateAnswer,
    CouncilMember,
    CouncilRun,
    ScoreResponse,
    ScoreReview,
    Settings,
    Vote,
    VoteResponse,
)
from council.ollama_client import OllamaClient
from council.prompts import build_answer_messages, build_score_messages, build_vote_messages
from council.storage import append_run
from council.utils import label_for_index
from council.voting import (
    aggregate_scores,
    count_votes,
    determine_score_winner,
    determine_winner,
    parse_score_response,
    parse_vote,
)


T = TypeVar("T")


async def run_fast_council(
    prompt: str,
    config: Settings | None = None,
    config_path: str | Path | None = None,
    *,
    stream_candidates: bool = False,
    on_candidate_chunk: Callable[[CouncilMember, str], None] | None = None,
) -> CouncilRun:
    settings = config or load_config(config_path)
    client = OllamaClient(
        settings.ollama.base_url,
        timeout_seconds=settings.ollama.request_timeout_seconds,
    )
    semaphore = asyncio.Semaphore(settings.ollama.max_parallel_requests)
    errors: list[str] = []

    answer_results = await asyncio.gather(
        *[
            _limited(
                semaphore,
                lambda member=member: _request_answer(
                    client,
                    member,
                    prompt,
                    stream=stream_candidates,
                    on_chunk=on_candidate_chunk,
                ),
            )
            for member in settings.council
        ],
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

    score_results = await asyncio.gather(
        *[
            _limited(
                semaphore,
                lambda member=member: _request_score(
                    client,
                    member,
                    prompt,
                    _eligible_answers(candidates, member),
                ),
            )
            for member in successful_members
        ],
        return_exceptions=True,
    )

    score_reviews: list[ScoreReview] = []
    for member, result in zip(successful_members, score_results):
        if isinstance(result, Exception):
            error = _format_model_error(member, result)
            errors.append(error)
            score_reviews.append(
                ScoreReview(
                    member_name=member.name,
                    model=member.model,
                    valid=False,
                    error=error,
                )
            )
            continue

        score_reviews.append(result)

    score_totals = aggregate_scores(score_reviews, labels)
    winner_label = determine_score_winner(score_totals)

    votes: list[Vote] = []
    vote_counts = {label: 0 for label in labels}
    if winner_label is None:
        vote_results = await asyncio.gather(
            *[
                _limited(
                    semaphore,
                    lambda member=member: _request_vote(
                        client,
                        member,
                        prompt,
                        _eligible_answers(candidates, member),
                    ),
                )
                for member in successful_members
            ],
            return_exceptions=True,
        )

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
        score_reviews=score_reviews,
        score_totals=score_totals,
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
    *,
    stream: bool = False,
    on_chunk: Callable[[CouncilMember, str], None] | None = None,
) -> str:
    messages = build_answer_messages(member.role, prompt)
    if stream:
        try:
            chunks: list[str] = []
            async for chunk in client.chat_stream(
                model=member.model,
                messages=messages,
                temperature=member.temperature,
            ):
                chunks.append(chunk)
                if on_chunk:
                    on_chunk(member, chunk)
            return "".join(chunks)
        except Exception:
            if on_chunk:
                on_chunk(member, "\n[stream failed; retrying without streaming]\n")

    return await client.chat(
        model=member.model,
        messages=messages,
        temperature=member.temperature,
    )


async def _request_vote(
    client: OllamaClient,
    member: CouncilMember,
    prompt: str,
    labeled_answers: dict[str, str],
) -> Vote:
    schema = VoteResponse.model_json_schema()
    raw_response = await client.chat(
        model=member.model,
        messages=build_vote_messages(member.role, prompt, labeled_answers, schema),
        temperature=0,
        format=schema,
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


async def _request_score(
    client: OllamaClient,
    member: CouncilMember,
    prompt: str,
    labeled_answers: dict[str, str],
) -> ScoreReview:
    schema = ScoreResponse.model_json_schema()
    raw_response = await client.chat(
        model=member.model,
        messages=build_score_messages(member.role, prompt, labeled_answers, schema),
        temperature=0,
        format=schema,
    )
    scores, best_label, valid, error = parse_score_response(
        raw_response,
        set(labeled_answers),
    )
    return ScoreReview(
        member_name=member.name,
        model=member.model,
        scores=scores,
        best_label=best_label,
        raw_response=raw_response,
        valid=valid,
        error=error,
    )


async def _limited(
    semaphore: asyncio.Semaphore,
    coro_factory: Callable[[], Awaitable[T]],
) -> T:
    async with semaphore:
        return await coro_factory()


def _eligible_answers(
    candidates: list[CandidateAnswer],
    member: CouncilMember,
) -> dict[str, str]:
    return {
        candidate.label: candidate.answer
        for candidate in candidates
        if candidate.member_name != member.name or candidate.model != member.model
    }


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
