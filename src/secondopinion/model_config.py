from __future__ import annotations

import os
from typing import Any


DEFAULT_CHEAP_MODEL = "gpt-5-nano"
DEFAULT_REASONING_EFFORT = "minimal"


def is_gpt5_model(model: str) -> bool:
    return model.strip().lower().startswith("gpt-5")


def default_reasoning_effort() -> str:
    return os.environ.get("SECONDOPINION_REASONING_EFFORT", DEFAULT_REASONING_EFFORT).strip() or DEFAULT_REASONING_EFFORT


def apply_chat_completion_cost_controls(body: dict[str, Any], *, model: str) -> None:
    if is_gpt5_model(model):
        body["reasoning_effort"] = default_reasoning_effort()
    else:
        body["temperature"] = 0
