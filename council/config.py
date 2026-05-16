from pathlib import Path

import yaml

from council.models import Settings


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> Settings:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not data:
        raise ValueError(f"{config_path} is empty")

    return Settings.model_validate(data)


def save_config(
    settings: Settings,
    path: str | Path = DEFAULT_CONFIG_PATH,
) -> None:
    config_path = Path(path)
    with config_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(
            settings.model_dump(mode="json"),
            file,
            sort_keys=False,
            allow_unicode=True,
        )
