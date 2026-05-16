from council.config import load_config


def test_default_config_uses_five_nemotron_members() -> None:
    settings = load_config()

    assert settings.ollama.request_timeout_seconds == 180
    assert len(settings.council) == 5
    assert {member.model for member in settings.council} == {"nemotron-3-nano:4b"}
    assert [member.name for member in settings.council] == [
        "Analyst",
        "Skeptic",
        "Builder",
        "Editor",
        "Synthesizer",
    ]
