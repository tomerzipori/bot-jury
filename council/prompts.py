import json


def build_answer_messages(member_role: str, user_prompt: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                f"You are a council member. Your role: {member_role}\n\n"
                "Answer the user's prompt independently. "
                "Be clear, useful, accurate, and direct. "
                "Do not mention that you are part of a council."
            ),
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]


def build_vote_messages(
    member_role: str,
    user_prompt: str,
    labeled_answers: dict[str, str],
    schema: dict[str, object] | None = None,
) -> list[dict[str, str]]:
    answers_text = "\n\n".join(
        f"{label}:\n{answer}" for label, answer in labeled_answers.items()
    )

    return [
        {
            "role": "system",
            "content": (
                f"You are a council reviewer. Your role: {member_role}\n\n"
                "You will review anonymized candidate answers. "
                "Choose the single best answer for the user's original prompt. "
                "Judge correctness, completeness, clarity, usefulness, and whether "
                "the answer follows the user's request. "
                "Do not prefer an answer because it resembles your own style."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Original user prompt:\n{user_prompt}\n\n"
                f"Candidate answers:\n{answers_text}\n\n"
                f"Return JSON only, matching this schema:\n{_schema_text(schema)}\n\n"
                "The vote must be one of the candidate labels."
            ),
        },
    ]


def build_score_messages(
    member_role: str,
    user_prompt: str,
    labeled_answers: dict[str, str],
    schema: dict[str, object] | None = None,
) -> list[dict[str, str]]:
    answers_text = "\n\n".join(
        f"{label}:\n{answer}" for label, answer in labeled_answers.items()
    )

    return [
        {
            "role": "system",
            "content": (
                f"You are a council reviewer. Your role: {member_role}\n\n"
                "You will review anonymized candidate answers. Score every "
                "candidate independently from 1 to 5 for correctness, completeness, "
                "clarity, usefulness, and safety. Higher safety means lower risk. "
                "Do not prefer an answer because it resembles your own style."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Original user prompt:\n{user_prompt}\n\n"
                f"Candidate answers:\n{answers_text}\n\n"
                f"Return JSON only, matching this schema:\n{_schema_text(schema)}\n\n"
                "Include exactly one score object for each candidate label. "
                "The best_label must be one of the candidate labels."
            ),
        },
    ]


def _schema_text(schema: dict[str, object] | None) -> str:
    if schema is None:
        return "{}"
    return json.dumps(schema, indent=2)
