from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import Any, Callable, Union

from .text import clean_text


PARSER_VERSION = "pypdf-v0.1"


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", value)
    return value.strip("-") or "item"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def pdf_store_dir(dataset: dict[str, Any], root: str | Path) -> Path:
    snapshot = dataset.get("source_snapshot") or {}
    source = safe_name(str(snapshot.get("source") or "manual"))
    venue = safe_name(str(snapshot.get("venue") or dataset.get("dataset") or "dataset"))
    year = safe_name(str(snapshot.get("year") or "unknown"))
    snapshot_id = safe_name(str(snapshot.get("snapshot_id") or "no-snapshot"))
    return Path(root) / source / venue.lower() / year / snapshot_id


def download_pdf(url: str, path: str | Path, timeout: int = 60) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/pdf,*/*",
            "User-Agent": "SecondOpinion-MVP/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
    path.write_bytes(data)
    return len(data)


def fetch_dataset_pdfs(
    dataset: dict[str, Any],
    *,
    root: str | Path = "data/pdfs",
    limit: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    store_dir = pdf_store_dir(dataset, root)
    store_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    created_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    papers = dataset.get("papers", [])
    if limit is not None:
        papers = papers[:limit]

    for paper in papers:
        paper_id = str(paper.get("paper_id") or "")
        pdf_url = str(paper.get("pdf_url") or "")
        relative_path = f"{safe_name(paper_id)}.pdf"
        pdf_path = store_dir / relative_path
        entry = {
            "paper_id": paper_id,
            "pdf_url": pdf_url,
            "path": relative_path,
            "status": "missing-url",
            "size_bytes": 0,
            "sha256": "",
            "error": "",
        }
        if not pdf_url:
            entries.append(entry)
            continue
        try:
            if force or not pdf_path.exists():
                download_pdf(pdf_url, pdf_path)
            entry["status"] = "ok"
            entry["size_bytes"] = pdf_path.stat().st_size
            entry["sha256"] = sha256_file(pdf_path)
        except Exception as exc:  # noqa: BLE001 - persist per-PDF failure in manifest.
            entry["status"] = "error"
            entry["error"] = str(exc)
        entries.append(entry)

    manifest = {
        "schema_version": "pdf-store-v0.1",
        "created_at": created_at,
        "dataset": dataset.get("dataset", "unknown"),
        "source_snapshot": dataset.get("source_snapshot"),
        "parser_version": PARSER_VERSION,
        "pdf_root": str(store_dir),
        "paper_count": len(entries),
        "pdf_count": sum(1 for entry in entries if entry["status"] == "ok"),
        "error_count": sum(1 for entry in entries if entry["status"] == "error"),
        "entries": entries,
    }
    write_json(store_dir / "manifest.json", manifest)
    return manifest


def extract_pdf_pages(pdf_path: str | Path) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF parsing requires pypdf. Install dependencies with `python3 -m pip install -e .`.") from exc

    reader = PdfReader(str(pdf_path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        pages.append({"page": index, "text": text})
    return pages


def infer_section(line: str, current: str) -> str:
    text = clean_text(line)
    if not text:
        return current
    lowered = text.lower()
    if lowered.startswith("abstract"):
        return "Abstract"
    if lowered.startswith("appendix"):
        return "Appendix"
    if lowered in {"references", "acknowledgements", "acknowledgments"}:
        return text.title()
    if re.match(r"^(?:[0-9]+|[A-Z])(?:\.[0-9]+)*\.?\s+[A-Z][A-Za-z0-9 ,:()/-]{2,80}$", text):
        return text
    return current


def append_chunk_text(buffer: list[str], line: str, max_chars: int, flush: Callable[[], None]) -> None:
    if sum(len(item) for item in buffer) + len(line) > max_chars:
        flush()
    buffer.append(line)


def chunk_page_text(
    *,
    paper_id: str,
    page: int,
    text: str,
    initial_section: str = "Unknown",
    max_chars: int = 1200,
) -> tuple[list[dict[str, Any]], str]:
    chunks = []
    section = initial_section
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        body = clean_text("\n".join(buffer))
        if not body:
            buffer = []
            return
        source_type = "appendix" if "appendix" in section.lower() else "paper"
        chunks.append(
            {
                "paper_id": paper_id,
                "source_type": source_type,
                "section": section,
                "page": page,
                "block_type": "paragraph",
                "text": body,
                "parser_version": PARSER_VERSION,
            }
        )
        buffer = []

    for block in re.split(r"\n\s*\n+", text):
        block = clean_text(block)
        if not block:
            continue
        for line in block.splitlines():
            line = clean_text(line)
            if not line:
                continue
            next_section = infer_section(line, section)
            if next_section != section:
                flush()
                section = next_section
                continue
            append_chunk_text(buffer, line, max_chars, flush)
    flush()
    return chunks, section


def extract_pdf_chunks(pdf_path: str | Path, *, paper_id: str, max_chars: int = 1200) -> list[dict[str, Any]]:
    pages = extract_pdf_pages(pdf_path)
    all_chunks: list[dict[str, Any]] = []
    section = "Unknown"
    for page in pages:
        chunks, section = chunk_page_text(
            paper_id=paper_id,
            page=int(page["page"]),
            text=page["text"],
            initial_section=section,
            max_chars=max_chars,
        )
        all_chunks.extend(chunks)
    return all_chunks


Extractor = Callable[[Union[str, Path], str], list[dict[str, Any]]]


def attach_pdf_chunks(
    dataset: dict[str, Any],
    pdf_manifest: dict[str, Any],
    *,
    extractor: Extractor | None = None,
) -> dict[str, Any]:
    extractor = extractor or (lambda path, paper_id: extract_pdf_chunks(path, paper_id=paper_id))
    pdf_root = Path(pdf_manifest["pdf_root"])
    by_paper_id = {entry["paper_id"]: entry for entry in pdf_manifest.get("entries", [])}
    attached = 0
    errors = []

    for paper in dataset.get("papers", []):
        paper_id = str(paper.get("paper_id") or "")
        entry = by_paper_id.get(paper_id)
        if not entry or entry.get("status") != "ok":
            paper["paper_sections"] = paper.get("paper_sections", [])
            continue
        try:
            chunks = extractor(pdf_root / entry["path"], paper_id)
            paper["paper_sections"] = chunks
            attached += len(chunks)
        except Exception as exc:  # noqa: BLE001 - keep dataset usable when one PDF fails.
            errors.append({"paper_id": paper_id, "error": str(exc)})
            paper["paper_sections"] = []

    dataset["evidence_store"] = {
        "schema_version": "evidence-store-v0.1",
        "parser_version": PARSER_VERSION,
        "pdf_manifest": str(Path(pdf_manifest["pdf_root"]) / "manifest.json"),
        "chunk_count": attached,
        "error_count": len(errors),
        "errors": errors,
    }
    return dataset


def build_evidence_store(
    dataset: dict[str, Any],
    *,
    pdf_root: str | Path = "data/pdfs",
    limit: int | None = None,
    force: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = fetch_dataset_pdfs(dataset, root=pdf_root, limit=limit, force=force)
    enriched = attach_pdf_chunks(dataset, manifest)
    return enriched, manifest
