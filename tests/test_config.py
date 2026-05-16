from council.config import load_config, save_config


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


def test_save_config_round_trips_member_edits(tmp_path) -> None:
    settings = load_config()
    settings.council[0].model = "other-model:1b"
    settings.council[0].role = "Use a different instruction."
    settings.council[0].temperature = 0.7

    config_path = tmp_path / "config.yaml"
    save_config(settings, config_path)
    reloaded = load_config(config_path)

    assert reloaded.council[0].model == "other-model:1b"
    assert reloaded.council[0].role == "Use a different instruction."
    assert reloaded.council[0].temperature == 0.7
