import json
import re

from pydantic import ValidationError

from council.models import CandidateScore, ScoreResponse, ScoreReview, Vote, VoteResponse


DEFAULT_SCORE_WEIGHTS = {
    "correctness": 0.35,
    "completeness": 0.25,
    "clarity": 0.15,
    "usefulness": 0.15,
    "safety": 0.10,
}


def parse_vote(
    raw_response: str,
    valid_labels: set[str],
) -> tuple[str | None, str, bool, str | None]:
    text = _strip_markdown_fence(raw_response.strip())
    json_text = _extract_first_json_object(text)
    if not json_text:
        return None, "", False, "No JSON object found in vote response"

    try:
        response = VoteResponse.model_validate_json(json_text)
    except ValidationError:
        pass
    else:
        return _validate_vote_response(response.vote, response.reason, valid_labels)

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        return None, "", False, f"Invalid JSON: {exc.msg}"

    if not isinstance(data, dict):
        return None, "", False, "Vote response must be a JSON object"

    return _validate_vote_response(data.get("vote"), data.get("reason", ""), valid_labels)


def _validate_vote_response(
    raw_vote: object,
    raw_reason: object,
    valid_labels: set[str],
) -> tuple[str | None, str, bool, str | None]:
    reason = raw_reason
    if not isinstance(reason, str):
        reason = str(reason)

    if not isinstance(raw_vote, str) or not raw_vote.strip():
        return None, reason, False, "Vote must be a non-empty string"

    vote = raw_vote.strip().upper()
    if vote not in valid_labels:
        labels = ", ".join(sorted(valid_labels))
        return vote, reason, False, f"Vote must be one of: {labels}"

    return vote, reason, True, None


def parse_score_response(
    raw_response: str,
    valid_labels: set[str],
) -> tuple[list[CandidateScore], str | None, bool, str | None]:
    text = _strip_markdown_fence(raw_response.strip())
    json_text = _extract_first_json_object(text)
    if not json_text:
        return [], None, False, "No JSON object found in score response"

    try:
        response = ScoreResponse.model_validate_json(json_text)
    except ValidationError as exc:
        return [], None, False, f"Invalid score response: {exc.errors()[0]['msg']}"

    best_label = _normalize_label(response.best_label)
    if best_label not in valid_labels:
        labels = ", ".join(sorted(valid_labels))
        return [], best_label, False, f"Best label must be one of: {labels}"

    normalized_scores: list[CandidateScore] = []
    seen_labels: set[str] = set()
    for score in response.scores:
        label = _normalize_label(score.label)
        if label not in valid_labels:
            labels = ", ".join(sorted(valid_labels))
            return [], label, False, f"Score label must be one of: {labels}"
        if label in seen_labels:
            return [], label, False, f"Duplicate score for label: {label}"

        seen_labels.add(label)
        normalized_scores.append(score.model_copy(update={"label": label}))

    if seen_labels != valid_labels:
        missing = ", ".join(sorted(valid_labels - seen_labels))
        return [], best_label, False, f"Missing scores for label(s): {missing}"

    return normalized_scores, best_label, True, None


def aggregate_scores(
    reviews: list[ScoreReview],
    labels: list[str],
    weights: dict[str, float] | None = None,
) -> dict[str, float]:
    score_weights = weights or DEFAULT_SCORE_WEIGHTS
    totals = {label: 0.0 for label in labels}
    counts = {label: 0 for label in labels}

    for review in reviews:
        if not review.valid:
            continue
        for score in review.scores:
            if score.label not in totals:
                continue
            totals[score.label] += weighted_score(score, score_weights)
            counts[score.label] += 1

    return {
        label: round(totals[label] / counts[label], 4)
        for label in labels
        if counts[label] > 0
    }


def weighted_score(
    score: CandidateScore,
    weights: dict[str, float] | None = None,
) -> float:
    score_weights = weights or DEFAULT_SCORE_WEIGHTS
    return sum(
        getattr(score, field) * weight for field, weight in score_weights.items()
    )


def determine_score_winner(score_totals: dict[str, float]) -> str | None:
    if not score_totals:
        return None

    ordered = sorted(score_totals.items(), key=lambda item: (-item[1], item[0]))
    top_label, top_score = ordered[0]
    if top_score <= 0:
        return None
    return top_label


def count_votes(votes: list[Vote], labels: list[str]) -> dict[str, int]:
    counts = {label: 0 for label in labels}
    for vote in votes:
        if vote.valid and vote.vote in counts:
            counts[vote.vote] += 1
    return counts


def determine_winner(vote_counts: dict[str, int]) -> str | None:
    if not vote_counts:
        return None

    ordered = sorted(vote_counts.items(), key=lambda item: item[1], reverse=True)
    top_label, top_count = ordered[0]
    if top_count == 0:
        return None

    if len(ordered) > 1 and ordered[1][1] == top_count:
        return None

    return top_label


def top_tied_labels(vote_counts: dict[str, int]) -> list[str]:
    if not vote_counts:
        return []

    top_count = max(vote_counts.values())
    if top_count == 0:
        return []

    labels = [label for label, count in vote_counts.items() if count == top_count]
    return labels if len(labels) > 1 else []


def _strip_markdown_fence(text: str) -> str:
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.I)
    if match:
        return match.group(1).strip()
    return text


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return text[start:]


def _normalize_label(label: str) -> str:
    return label.strip().upper()
