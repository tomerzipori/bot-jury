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
                "Return JSON only, with this exact schema:\n"
                "{\n"
                '  "vote": "A",\n'
                '  "reason": "Brief reason for your vote."\n'
                "}\n\n"
                "The vote must be one of the candidate labels."
            ),
        },
    ]
