from __future__ import annotations

import html
import re
from typing import Any, Iterable


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "paper",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "with",
}


def unwrap_content_value(value: Any) -> Any:
    """Handle both OpenReview v1 raw content and v2 {'value': ...} content."""
    if isinstance(value, dict) and "value" in value:
        return value.get("value")
    return value


def text_from_content(content: dict[str, Any], keys: Iterable[str]) -> str:
    parts: list[str] = []
    for key in keys:
        if key not in content:
            continue
        value = unwrap_content_value(content[key])
        if value is None:
            continue
        if isinstance(value, list):
            parts.extend(str(item) for item in value if item is not None)
        else:
            parts.append(str(value))
    return clean_text("\n\n".join(parts))


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "item"


def split_review_sentences(text: str) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    bullet_lines = []
    for line in text.splitlines():
        line = line.strip(" -*\t")
        if line:
            bullet_lines.append(line)
    flattened = " ".join(bullet_lines)
    pieces = re.split(r"(?<=[.!?])\s+|;\s+|\n+", flattened)
    return [piece.strip() for piece in pieces if len(piece.strip()) > 12]


def tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
        if token not in STOPWORDS
    }


def first_number(text: str) -> float | None:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text or "")
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None

