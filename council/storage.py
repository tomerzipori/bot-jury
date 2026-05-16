from pathlib import Path

from council.models import CouncilRun


def append_run(path: str, run: CouncilRun) -> None:
    output_path = Path(path)
    if output_path.parent != Path("."):
        output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("a", encoding="utf-8") as file:
        file.write(run.model_dump_json() + "\n")
