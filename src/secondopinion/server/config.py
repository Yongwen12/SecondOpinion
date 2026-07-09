from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SCORER_VERSION = "server-hybrid-scorer-v0.1"
DEFAULT_MEMORY_INDEX_VERSION = "external-full-lite-v0.1"


@dataclass(frozen=True)
class ServerSettings:
    database_url: str
    artifact_root: Path
    scoring_memory_path: Path
    home_snapshot_path: Path = Path("frontend/data/home_2025.json")
    scorer_version: str = DEFAULT_SCORER_VERSION
    memory_index_version: str = DEFAULT_MEMORY_INDEX_VERSION
    cors_origins: tuple[str, ...] = ()
    max_claims_per_review: int = 8
    llm_scorer_enabled: bool = False
    llm_scorer_model: str = "gpt-5-nano"


def settings_from_env() -> ServerSettings:
    origins = tuple(
        origin.strip()
        for origin in os.environ.get("SECONDOPINION_CORS_ORIGINS", "").split(",")
        if origin.strip()
    )
    return ServerSettings(
        database_url=os.environ.get("SECONDOPINION_DATABASE_URL", "sqlite:///data/server/secondopinion.db"),
        artifact_root=Path(os.environ.get("SECONDOPINION_SERVER_ARTIFACT_ROOT", "data/server")),
        scoring_memory_path=Path(
            os.environ.get(
                "SECONDOPINION_SCORING_MEMORY",
                "data/normalized/scoring_memory_external_full_lite_v0.1.jsonl",
            )
        ),
        home_snapshot_path=Path(os.environ.get("SECONDOPINION_HOME_SNAPSHOT", "frontend/data/home_2025.json")),
        scorer_version=os.environ.get("SECONDOPINION_SCORER_VERSION", DEFAULT_SCORER_VERSION),
        memory_index_version=os.environ.get("SECONDOPINION_MEMORY_INDEX_VERSION", DEFAULT_MEMORY_INDEX_VERSION),
        cors_origins=origins,
        max_claims_per_review=int(os.environ.get("SECONDOPINION_MAX_CLAIMS_PER_REVIEW", "8")),
        llm_scorer_enabled=os.environ.get("SECONDOPINION_ENABLE_LLM_SCORER", "0").lower() in {"1", "true", "yes"},
        llm_scorer_model=os.environ.get("SECONDOPINION_SCORER_MODEL", os.environ.get("SECONDOPINION_JUDGE_MODEL", "gpt-5-nano")),
    )


def normalized_inputs_from_env() -> list[Path]:
    configured = os.environ.get("SECONDOPINION_NORMALIZED_INPUTS", "")
    if configured:
        return [Path(item.strip()) for item in configured.split(",") if item.strip()]
    return [
        Path("data/normalized/iclr_2022_sample_1000.json"),
        Path("data/normalized/iclr_2023_sample_1000.json"),
        Path("data/normalized/iclr_2024_sample_1000.json"),
        Path("data/normalized/iclr_2025_sample_1000.json"),
    ]

