from council.voting import parse_vote


def test_parse_vote_clean_json() -> None:
    vote, reason, valid, error = parse_vote(
        '{"vote": "A", "reason": "Best answer."}',
        {"A", "B"},
    )

    assert (vote, reason, valid, error) == ("A", "Best answer.", True, None)


def test_parse_vote_markdown_fence() -> None:
    vote, reason, valid, error = parse_vote(
        '```json\n{"vote": "B", "reason": "Clearer."}\n```',
        {"A", "B"},
    )

    assert (vote, reason, valid, error) == ("B", "Clearer.", True, None)


def test_parse_vote_extra_text_around_json() -> None:
    vote, reason, valid, error = parse_vote(
        'I choose this:\n{"vote": "A", "reason": "More complete."}\nDone.',
        {"A", "B"},
    )

    assert (vote, reason, valid, error) == ("A", "More complete.", True, None)


def test_parse_vote_invalid_json() -> None:
    vote, reason, valid, error = parse_vote('{"vote": "A",', {"A", "B"})

    assert vote is None
    assert reason == ""
    assert valid is False
    assert error is not None
    assert "Invalid JSON" in error


def test_parse_vote_outside_valid_labels() -> None:
    vote, reason, valid, error = parse_vote(
        '{"vote": "Z", "reason": "Looks good."}',
        {"A", "B"},
    )

    assert vote == "Z"
    assert reason == "Looks good."
    assert valid is False
    assert error == "Vote must be one of: A, B"
