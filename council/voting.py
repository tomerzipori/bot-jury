import json
import re

from council.models import Vote


def parse_vote(
    raw_response: str,
    valid_labels: set[str],
) -> tuple[str | None, str, bool, str | None]:
    text = _strip_markdown_fence(raw_response.strip())
    json_text = _extract_first_json_object(text)
    if not json_text:
        return None, "", False, "No JSON object found in vote response"

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        return None, "", False, f"Invalid JSON: {exc.msg}"

    if not isinstance(data, dict):
        return None, "", False, "Vote response must be a JSON object"

    raw_vote = data.get("vote")
    reason = data.get("reason", "")
    if not isinstance(reason, str):
        reason = str(reason)

    if not isinstance(raw_vote, str) or not raw_vote.strip():
        return None, reason, False, "Vote must be a non-empty string"

    vote = raw_vote.strip().upper()
    if vote not in valid_labels:
        labels = ", ".join(sorted(valid_labels))
        return vote, reason, False, f"Vote must be one of: {labels}"

    return vote, reason, True, None


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
