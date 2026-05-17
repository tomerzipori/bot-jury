import os
import shutil
import sys
from importlib import resources
from pathlib import Path

import yaml

from council.models import Settings


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
CONFIG_ENV_VAR = "BOT_JURY_CONFIG"
APP_CONFIG_DIR_NAME = "bot-jury"


def default_user_config_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / APP_CONFIG_DIR_NAME / "config.yaml"

    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / APP_CONFIG_DIR_NAME
            / "config.yaml"
        )

    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / (
        APP_CONFIG_DIR_NAME
    ) / "config.yaml"


def resolve_config_path(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path).expanduser()

    env_path = os.environ.get(CONFIG_ENV_VAR)
    if env_path:
        return Path(env_path).expanduser()

    return default_user_config_path()


def ensure_config_file(path: str | Path | None = None) -> Path:
    config_path = resolve_config_path(path)
    if config_path.exists():
        return config_path

    config_path.parent.mkdir(parents=True, exist_ok=True)
    if DEFAULT_CONFIG_PATH.exists():
        shutil.copyfile(DEFAULT_CONFIG_PATH, config_path)
    else:
        default_config = resources.files("council").joinpath("default_config.yaml")
        config_path.write_text(
            default_config.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    return config_path


def load_config(path: str | Path | None = None) -> Settings:
    config_path = ensure_config_file(path)
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not data:
        raise ValueError(f"{config_path} is empty")

    return Settings.model_validate(data)


def save_config(
    settings: Settings,
    path: str | Path | None = None,
) -> None:
    config_path = resolve_config_path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(
            settings.model_dump(mode="json"),
            file,
            sort_keys=False,
            allow_unicode=True,
        )
