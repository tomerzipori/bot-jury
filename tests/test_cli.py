import pytest

from council import cli


def test_cli_help_prints_entrypoint_usage(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.app(["--help"])

    assert exc_info.value.code == 0
    assert "bot-jury" in capsys.readouterr().out
