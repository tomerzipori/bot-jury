import app
from council.models import AppSettings, CouncilMember, OllamaSettings, Settings


def _settings(member_name: str = "Analyst") -> Settings:
    return Settings(
        ollama=OllamaSettings(base_url="http://localhost:11434"),
        app=AppSettings(runs_path="runs.jsonl"),
        council=[
            CouncilMember(
                name=member_name,
                model="test-model:1b",
                role="Answer clearly.",
            )
        ],
    )


def _quiet_console(monkeypatch) -> None:
    monkeypatch.setattr(app.console, "print", lambda *args, **kwargs: None)


def test_main_returns_to_action_menu_after_run(monkeypatch) -> None:
    settings = _settings()
    actions = iter(["", "q"])
    headers = []
    runs = []

    _quiet_console(monkeypatch)
    monkeypatch.setattr(app, "load_config", lambda: settings)
    monkeypatch.setattr(app, "_render_header", lambda current: headers.append(current))
    monkeypatch.setattr(app, "_read_start_action", lambda: next(actions))
    monkeypatch.setattr(app, "_run_council", lambda current: runs.append(current))

    app._main()

    assert headers == [settings, settings]
    assert runs == [settings]


def test_main_can_run_twice_in_one_session(monkeypatch) -> None:
    settings = _settings()
    actions = iter(["", "", "q"])
    runs = []

    _quiet_console(monkeypatch)
    monkeypatch.setattr(app, "load_config", lambda: settings)
    monkeypatch.setattr(app, "_render_header", lambda current: None)
    monkeypatch.setattr(app, "_read_start_action", lambda: next(actions))
    monkeypatch.setattr(app, "_run_council", lambda current: runs.append(current))

    app._main()

    assert runs == [settings, settings]


def test_main_configure_returns_to_action_menu(monkeypatch) -> None:
    original = _settings("Original")
    edited = _settings("Edited")
    actions = iter(["c", "", "q"])
    headers = []
    configured = []
    runs = []

    _quiet_console(monkeypatch)
    monkeypatch.setattr(app, "load_config", lambda: original)
    monkeypatch.setattr(app, "_render_header", lambda current: headers.append(current))
    monkeypatch.setattr(app, "_read_start_action", lambda: next(actions))
    monkeypatch.setattr(
        app,
        "_configure_settings",
        lambda current: configured.append(current) or edited,
    )
    monkeypatch.setattr(app, "_run_council", lambda current: runs.append(current))

    app._main()

    assert configured == [original]
    assert headers == [original, edited, edited]
    assert runs == [edited]


def test_main_quit_exits_without_running(monkeypatch) -> None:
    settings = _settings()
    runs = []

    _quiet_console(monkeypatch)
    monkeypatch.setattr(app, "load_config", lambda: settings)
    monkeypatch.setattr(app, "_render_header", lambda current: None)
    monkeypatch.setattr(app, "_read_start_action", lambda: "q")
    monkeypatch.setattr(app, "_run_council", lambda current: runs.append(current))

    app._main()

    assert runs == []
