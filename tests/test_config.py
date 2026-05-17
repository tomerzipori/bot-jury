from council.config import (
    CONFIG_ENV_VAR,
    DEFAULT_CONFIG_PATH,
    default_user_config_path,
    load_config,
    resolve_config_path,
    save_config,
)


def test_default_config_uses_five_nemotron_members() -> None:
    settings = load_config(DEFAULT_CONFIG_PATH)

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
    settings = load_config(DEFAULT_CONFIG_PATH)
    settings.council[0].model = "other-model:1b"
    settings.council[0].role = "Use a different instruction."
    settings.council[0].temperature = 0.7

    config_path = tmp_path / "config.yaml"
    save_config(settings, config_path)
    reloaded = load_config(config_path)

    assert reloaded.council[0].model == "other-model:1b"
    assert reloaded.council[0].role == "Use a different instruction."
    assert reloaded.council[0].temperature == 0.7


def test_resolve_config_path_uses_env_override(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "custom.yaml"
    monkeypatch.setenv(CONFIG_ENV_VAR, str(config_path))

    assert resolve_config_path() == config_path


def test_load_config_copies_default_to_user_path(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    user_path = default_user_config_path()
    assert not user_path.exists()

    settings = load_config()

    assert user_path.exists()
    assert len(settings.council) == 5


def test_save_config_creates_parent_directories(tmp_path) -> None:
    settings = load_config(DEFAULT_CONFIG_PATH)
    config_path = tmp_path / "nested" / "config.yaml"

    save_config(settings, config_path)

    assert config_path.exists()
