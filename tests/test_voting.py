from council.models import Vote
from council.voting import count_votes, determine_winner


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
