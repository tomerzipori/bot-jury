import httpx


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, timeout_seconds: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
    ) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError as exc:
            raise OllamaError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running."
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = _response_detail(exc.response)
            raise OllamaError(
                f"Ollama request failed for model {model}: "
                f"{exc.response.status_code} {detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaError(f"Ollama request failed for model {model}: {exc}") from exc
        except ValueError as exc:
            raise OllamaError(f"Ollama returned invalid JSON for model {model}") from exc

        content = data.get("message", {}).get("content")
        if not isinstance(content, str):
            raise OllamaError(f"Ollama response for model {model} did not include content")

        return content

    async def list_models(self) -> set[str]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError as exc:
            raise OllamaError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running."
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = _response_detail(exc.response)
            raise OllamaError(
                f"Ollama model check failed: {exc.response.status_code} {detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaError(f"Ollama model check failed: {exc}") from exc
        except ValueError as exc:
            raise OllamaError("Ollama returned invalid JSON while listing models") from exc

        models = data.get("models", [])
        names: set[str] = set()
        if not isinstance(models, list):
            return names

        for model in models:
            if not isinstance(model, dict):
                continue
            for key in ("name", "model"):
                name = model.get(key)
                if isinstance(name, str):
                    names.add(name)

        return names


def _response_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text[:300]

    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, str):
            return error

    return response.text[:300]
