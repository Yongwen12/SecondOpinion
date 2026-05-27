from __future__ import annotations

from importlib.resources import files
from typing import Any


def load_prompt(name: str, **values: Any) -> str:
    prompt = files("secondopinion.prompts").joinpath(name).read_text(encoding="utf-8")
    for key, value in values.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
    return prompt.strip()
