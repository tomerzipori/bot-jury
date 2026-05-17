from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any

import httpx
from ollama import AsyncClient, ResponseError


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: int = 120,
        client: AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client = client or AsyncClient(host=self.base_url, timeout=timeout_seconds)

    async def chat(
        self,
        model: str,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.3,
        *,
        format: str | dict[str, Any] | None = None,
        options: Mapping[str, Any] | None = None,
    ) -> str:
        merged_options: dict[str, Any] = {"temperature": temperature}
        if options:
            merged_options.update(options)

        try:
            response = await self.client.chat(
                model=model,
                messages=list(messages),
                stream=False,
                format=format,
                options=merged_options,
            )
        except Exception as exc:
            raise _normalize_error(exc, self.base_url, self.timeout_seconds, model) from exc

        content = _message_content(response)
        if not isinstance(content, str):
            raise OllamaError(f"Ollama response for model {model} did not include content")

        return content

    async def chat_stream(
        self,
        model: str,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.3,
        *,
        format: str | dict[str, Any] | None = None,
        options: Mapping[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        merged_options: dict[str, Any] = {"temperature": temperature}
        if options:
            merged_options.update(options)

        try:
            stream = await self.client.chat(
                model=model,
                messages=list(messages),
                stream=True,
                format=format,
                options=merged_options,
            )
            async for chunk in stream:
                content = _message_content(chunk)
                if isinstance(content, str):
                    yield content
        except Exception as exc:
            raise _normalize_error(exc, self.base_url, self.timeout_seconds, model) from exc

    async def list_models(self) -> set[str]:
        try:
            response = await self.client.list()
        except Exception as exc:
            raise _normalize_error(exc, self.base_url, self.timeout_seconds) from exc

        names: set[str] = set()
        models = _field(response, "models", [])
        if not isinstance(models, Sequence):
            return names

        for model in models:
            for key in ("model", "name"):
                name = _field(model, key)
                if isinstance(name, str):
                    names.add(name)

        return names

    async def show_model(self, model: str) -> Mapping[str, Any]:
        try:
            response = await self.client.show(model)
        except Exception as exc:
            raise _normalize_error(exc, self.base_url, self.timeout_seconds, model) from exc

        return _dump_response(response)

    async def pull_model(self, model: str) -> list[str]:
        try:
            response = await self.client.pull(model, stream=False)
        except Exception as exc:
            raise _normalize_error(exc, self.base_url, self.timeout_seconds, model) from exc

        status = _field(response, "status")
        return [status] if isinstance(status, str) else []


def _normalize_error(
    error: Exception,
    base_url: str,
    timeout_seconds: int,
    model: str | None = None,
) -> OllamaError:
    target = f" for model {model}" if model else ""
    if isinstance(error, OllamaError):
        return error
    if isinstance(error, httpx.ConnectError):
        return OllamaError(
            f"Could not connect to Ollama at {base_url}. Make sure Ollama is running."
        )
    if isinstance(error, httpx.TimeoutException):
        return OllamaError(
            f"Ollama request{target} timed out after {timeout_seconds} seconds"
        )
    if isinstance(error, ResponseError):
        status = f"{error.status_code} " if error.status_code >= 0 else ""
        return OllamaError(f"Ollama request{target} failed: {status}{error.error}")
    if isinstance(error, httpx.HTTPStatusError):
        return OllamaError(
            f"Ollama request{target} failed: {error.response.status_code} "
            f"{error.response.text[:300]}"
        )
    if isinstance(error, httpx.RequestError):
        return OllamaError(f"Ollama request{target} failed: {error}")
    return OllamaError(f"Ollama request{target} failed: {error}")


def _message_content(response: Any) -> str | None:
    message = _field(response, "message")
    content = _field(message, "content")
    return content if isinstance(content, str) else None


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _dump_response(response: Any) -> Mapping[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    if isinstance(response, Mapping):
        return dict(response)
    return {"response": str(response)}
