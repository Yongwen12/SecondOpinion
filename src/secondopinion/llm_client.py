from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class LLMClientError(RuntimeError):
    pass


class OpenAIChatClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 90,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "OpenAIChatClient":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise LLMClientError(
                "OPENAI_API_KEY is required for LLM calls. "
                "Set it in your shell or create a local .env from .env.example."
            )
        return cls(
            api_key=api_key,
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )

    def complete_json(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        body = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"OpenAI API request failed: {message}") from exc
        except urllib.error.URLError as exc:
            raise LLMClientError(f"OpenAI API request failed: {exc}") from exc

        message = payload.get("choices", [{}])[0].get("message", {})
        if message.get("refusal"):
            raise LLMClientError(f"OpenAI model refused claim extraction: {message['refusal']}")
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not isinstance(content, str) or not content.strip():
            raise LLMClientError("OpenAI API returned an empty structured output.")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMClientError("OpenAI API returned non-JSON content despite structured output request.") from exc
