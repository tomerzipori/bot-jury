from council.models import CandidateScore, ScoreReview, Vote
from council.voting import (
    aggregate_scores,
    count_votes,
    determine_score_winner,
    determine_winner,
    parse_score_response,
)


def test_count_votes_counts_valid_votes() -> None:
    votes = [
        Vote(member_name="One", model="a", vote="A", valid=True),
        Vote(member_name="Two", model="b", vote="C", valid=True),
        Vote(member_name="Three", model="c", vote="C", valid=True),
    ]

    assert count_votes(votes, ["A", "B", "C"]) == {"A": 1, "B": 0, "C": 2}


def test_count_votes_ignores_invalid_votes() -> None:
    votes = [
        Vote(member_name="One", model="a", vote="A", valid=True),
        Vote(member_name="Two", model="b", vote="B", valid=False),
        Vote(member_name="Three", model="c", vote="Z", valid=True),
    ]

    assert count_votes(votes, ["A", "B"]) == {"A": 1, "B": 0}


def test_determine_winner_returns_none_for_tie() -> None:
    assert determine_winner({"A": 2, "B": 2, "C": 1}) is None


def test_determine_winner_returns_clear_winner() -> None:
    assert determine_winner({"A": 1, "B": 3, "C": 0}) == "B"


def test_determine_winner_returns_none_for_no_valid_votes() -> None:
    assert determine_winner({"A": 0, "B": 0}) is None


def test_parse_score_response_valid_structured_json() -> None:
    scores, best_label, valid, error = parse_score_response(
        """
        {
          "scores": [
            {
              "label": "a",
              "correctness": 5,
              "completeness": 4,
              "clarity": 5,
              "usefulness": 5,
              "safety": 4,
              "reason": "Strongest."
            },
            {
              "label": " B ",
              "correctness": 3,
              "completeness": 3,
              "clarity": 4,
              "usefulness": 3,
              "safety": 5,
              "reason": "Good but thinner."
            }
          ],
          "best_label": " A "
        }
        """,
        {"A", "B"},
    )

    assert valid is True
    assert error is None
    assert best_label == "A"
    assert [score.label for score in scores] == ["A", "B"]


def test_parse_score_response_rejects_invalid_label() -> None:
    scores, best_label, valid, error = parse_score_response(
        """
        {
          "scores": [
            {
              "label": "Z",
              "correctness": 5,
              "completeness": 5,
              "clarity": 5,
              "usefulness": 5,
              "safety": 5,
              "reason": "Bad label."
            }
          ],
          "best_label": "Z"
        }
        """,
        {"A"},
    )

    assert scores == []
    assert best_label == "Z"
    assert valid is False
    assert error == "Best label must be one of: A"


def test_parse_score_response_rejects_missing_category() -> None:
    scores, best_label, valid, error = parse_score_response(
        """
        {
          "scores": [
            {
              "label": "A",
              "correctness": 5,
              "completeness": 5,
              "clarity": 5,
              "usefulness": 5,
              "reason": "Missing safety."
            }
          ],
          "best_label": "A"
        }
        """,
        {"A"},
    )

    assert scores == []
    assert best_label is None
    assert valid is False
    assert error is not None
    assert "Invalid score response" in error


def test_parse_score_response_rejects_out_of_range_scores() -> None:
    scores, best_label, valid, error = parse_score_response(
        """
        {
          "scores": [
            {
              "label": "A",
              "correctness": 6,
              "completeness": 5,
              "clarity": 5,
              "usefulness": 5,
              "safety": 5,
              "reason": "Too high."
            }
          ],
          "best_label": "A"
        }
        """,
        {"A"},
    )

    assert scores == []
    assert best_label is None
    assert valid is False
    assert error is not None
    assert "Invalid score response" in error


def test_aggregate_scores_uses_weighted_average() -> None:
    review = ScoreReview(
        member_name="Reviewer",
        model="model",
        scores=[
            CandidateScore(
                label="A",
                correctness=5,
                completeness=5,
                clarity=5,
                usefulness=5,
                safety=5,
                reason="Best.",
            ),
            CandidateScore(
                label="B",
                correctness=1,
                completeness=1,
                clarity=1,
                usefulness=1,
                safety=1,
                reason="Weak.",
            ),
        ],
    )

    assert aggregate_scores([review], ["A", "B"]) == {"A": 5.0, "B": 1.0}


def test_determine_score_winner_breaks_ties_by_label() -> None:
    assert determine_score_winner({"B": 4.0, "A": 4.0}) == "A"
