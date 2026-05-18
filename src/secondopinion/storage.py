from __future__ import annotations

import os
from pathlib import Path


STORAGE_ROOT_ENV = "SECONDOPINION_STORAGE_ROOT"
ARTIFACT_TOP_LEVEL_DIRS = {"data", "reports"}


def storage_root(explicit_root: str | Path | None = None) -> Path | None:
    value = explicit_root or os.environ.get(STORAGE_ROOT_ENV)
    if not value:
        return None
    return Path(value).expanduser()


def is_artifact_path(path: str | Path) -> bool:
    path = Path(path)
    return bool(path.parts) and path.parts[0] in ARTIFACT_TOP_LEVEL_DIRS


def resolve_artifact_path(path: str | Path, *, root: str | Path | None = None) -> Path:
    path = Path(path).expanduser()
    if path.is_absolute():
        return path
    base = storage_root(root)
    if base is None or not is_artifact_path(path):
        return path
    return base / path


def discover_google_drive_roots() -> list[Path]:
    cloud_storage = Path.home() / "Library" / "CloudStorage"
    if not cloud_storage.exists():
        return []
    return sorted(path / "My Drive" for path in cloud_storage.glob("GoogleDrive-*") if (path / "My Drive").exists())


def suggested_drive_storage_root(folder_name: str = "SecondOpinionData") -> Path | None:
    roots = discover_google_drive_roots()
    if not roots:
        return None
    return roots[0] / folder_name
