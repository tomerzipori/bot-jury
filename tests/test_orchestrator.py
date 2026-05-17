import asyncio
import json
import re

import pytest

from council.models import AppSettings, CouncilMember, OllamaSettings, Settings
from council.orchestrator import run_fast_council


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _settings(tmp_path, max_parallel_requests: int = 2) -> Settings:
    return Settings(
        ollama=OllamaSettings(
            base_url="http://localhost:11434",
            request_timeout_seconds=120,
            max_parallel_requests=max_parallel_requests,
        ),
        app=AppSettings(runs_path=str(tmp_path / "runs.jsonl")),
        council=[
            CouncilMember(name="One", model="model-one", role="Role one."),
            CouncilMember(name="Two", model="model-two", role="Role two."),
            CouncilMember(name="Three", model="model-three", role="Role three."),
        ],
    )


class _ConcurrencyFakeClient:
    active = 0
    max_active = 0

    def __init__(self, *_args, **_kwargs):
        pass

    async def chat(self, model, messages, **_kwargs):
        type(self).active += 1
        type(self).max_active = max(type(self).max_active, type(self).active)
        try:
            await asyncio.sleep(0.01)
            content = messages[1]["content"]
            system = messages[0]["content"]
            if "Score every" in system:
                labels = re.findall(r"(?:^|\n)([A-Z]+):\n", content)
                return json.dumps(
                    {
                        "scores": [
                            {
                                "label": label,
                                "correctness": 5 if index == 0 else 1,
                                "completeness": 5 if index == 0 else 1,
                                "clarity": 5 if index == 0 else 1,
                                "usefulness": 5 if index == 0 else 1,
                                "safety": 5 if index == 0 else 1,
                                "reason": "Scored.",
                            }
                            for index, label in enumerate(labels)
                        ],
                        "best_label": labels[0],
                    }
                )
            return f"answer from {model}"
        finally:
            type(self).active -= 1


@pytest.mark.anyio
async def test_run_fast_council_respects_concurrency_limit(tmp_path, monkeypatch) -> None:
    _ConcurrencyFakeClient.active = 0
    _ConcurrencyFakeClient.max_active = 0
    monkeypatch.setattr("council.orchestrator.OllamaClient", _ConcurrencyFakeClient)

    run = await run_fast_council(
        "prompt",
        config=_settings(tmp_path, max_parallel_requests=1),
    )

    assert _ConcurrencyFakeClient.max_active == 1
    assert run.winner_label == "A"
    assert run.score_totals
    assert run.votes == []


class _FallbackFakeClient:
    def __init__(self, *_args, **_kwargs):
        pass

    async def chat(self, model, messages, **_kwargs):
        content = messages[1]["content"]
        system = messages[0]["content"]
        if "Score every" in system:
            return "not json"
        if "Choose the single best" in system:
            labels = re.findall(r"(?:^|\n)([A-Z]+):\n", content)
            return json.dumps({"vote": labels[0], "reason": "Fallback."})
        return f"answer from {model}"


@pytest.mark.anyio
async def test_run_fast_council_falls_back_to_votes_when_scoring_fails(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("council.orchestrator.OllamaClient", _FallbackFakeClient)

    run = await run_fast_council("prompt", config=_settings(tmp_path))

    assert run.score_totals == {}
    assert run.votes
    assert run.winner_label == "A"
