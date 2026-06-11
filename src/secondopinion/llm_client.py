from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .model_config import apply_chat_completion_cost_controls


class LLMClientError(RuntimeError):
    pass


class OpenAIChatClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 90,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    @classmethod
    def from_env(cls) -> "OpenAIChatClient":
        load_dotenv()
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise LLMClientError(
                "OPENAI_API_KEY is required for LLM calls. "
                "Set it in your shell or create a local .env from .env.example."
            )
        return cls(
            api_key=api_key,
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            timeout=int(os.environ.get("OPENAI_TIMEOUT", "180")),
            max_retries=int(os.environ.get("OPENAI_MAX_RETRIES", "2")),
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
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        apply_chat_completion_cost_controls(body, model=model)
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                message = exc.read().decode("utf-8", errors="replace")
                if attempt < self.max_retries and exc.code in {408, 409, 429, 500, 502, 503, 504}:
                    time.sleep(2 ** attempt)
                    continue
                raise LLMClientError(f"OpenAI API request failed: {message}") from exc
            except (TimeoutError, urllib.error.URLError) as exc:
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise LLMClientError(f"OpenAI API request failed: {exc}") from exc
        else:
            raise LLMClientError("OpenAI API request failed after retries.")

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


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
