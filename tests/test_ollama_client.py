import pytest
from ollama import ResponseError

from council.ollama_client import OllamaClient, OllamaError


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _Message:
    def __init__(self, content: str):
        self.content = content


class _ChatResponse:
    def __init__(self, content: str):
        self.message = _Message(content)


class _Model:
    def __init__(self, model: str):
        self.model = model


class _ListResponse:
    def __init__(self, models):
        self.models = models


@pytest.mark.anyio
async def test_chat_forwards_structured_format_and_options() -> None:
    calls = []

    class FakeAsyncClient:
        async def chat(self, **kwargs):
            calls.append(kwargs)
            return _ChatResponse("hello")

    client = OllamaClient(
        "http://localhost:11434",
        client=FakeAsyncClient(),
    )

    result = await client.chat(
        "model",
        [{"role": "user", "content": "hi"}],
        temperature=0,
        format={"type": "object"},
        options={"num_ctx": 1024},
    )

    assert result == "hello"
    assert calls == [
        {
            "model": "model",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
            "format": {"type": "object"},
            "options": {"temperature": 0, "num_ctx": 1024},
        }
    ]


@pytest.mark.anyio
async def test_chat_normalizes_ollama_response_error() -> None:
    class FakeAsyncClient:
        async def chat(self, **kwargs):
            raise ResponseError("missing model", status_code=404)

    client = OllamaClient(
        "http://localhost:11434",
        client=FakeAsyncClient(),
    )

    with pytest.raises(OllamaError, match="404 missing model"):
        await client.chat("missing", [{"role": "user", "content": "hi"}])


@pytest.mark.anyio
async def test_list_models_extracts_model_names() -> None:
    class FakeAsyncClient:
        async def list(self):
            return _ListResponse([_Model("alpha:1b"), {"name": "beta:2b"}])

    client = OllamaClient(
        "http://localhost:11434",
        client=FakeAsyncClient(),
    )

    assert await client.list_models() == {"alpha:1b", "beta:2b"}


@pytest.mark.anyio
async def test_chat_stream_yields_content_chunks() -> None:
    async def chunks():
        yield _ChatResponse("a")
        yield _ChatResponse("b")

    class FakeAsyncClient:
        async def chat(self, **kwargs):
            assert kwargs["stream"] is True
            return chunks()

    client = OllamaClient(
        "http://localhost:11434",
        client=FakeAsyncClient(),
    )

    result = [
        chunk
        async for chunk in client.chat_stream(
            "model",
            [{"role": "user", "content": "hi"}],
        )
    ]

    assert result == ["a", "b"]
