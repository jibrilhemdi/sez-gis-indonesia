from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest_entry(path: Path) -> None:
    """Reject changed existing source files instead of silently blessing a rerun."""
    manifest = ROOT / "metadata/file_manifest.csv"
    if not manifest.exists():
        raise ValueError(f"No manifest for existing file: {path}")
    with manifest.open(newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["path"] == relative(path)]
    if len(rows) != 1 or path.stat().st_size != int(rows[0]["bytes"]) or sha256(path) != rows[0]["sha256"]:
        raise ValueError(f"Existing file differs from manifest: {path}")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


MANIFEST_FIELDS = ["path", "source_id", "bytes", "sha256", "format", "spatial_extent", "temporal_extent", "rows_or_dimensions", "validation_status", "parent_files", "transformation_command", "retrieved_at", "http_last_modified", "http_etag"]


def upsert_csv(path: Path, fields: list[str], row: dict[str, Any], key: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    old: list[dict[str, str]] = []
    if path.exists():
        with path.open(newline="") as handle:
            old = list(csv.DictReader(handle))
    old = [item for item in old if item.get(key) != str(row[key])]
    old.append({field: "" if row.get(field) is None else str(row.get(field, "")) for field in fields})
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(old)
    temp.replace(path)


def register(path: Path, source_id: str, fmt: str, *, status: str = "verified", extent: str = "", temporal: str = "", rows: str = "", parents: str = "", command: str = "", headers: dict[str, str] | None = None) -> None:
    headers = headers or {}
    upsert_csv(ROOT / "metadata/file_manifest.csv", MANIFEST_FIELDS, {
        "path": relative(path), "source_id": source_id, "bytes": path.stat().st_size,
        "sha256": sha256(path), "format": fmt, "spatial_extent": extent,
        "temporal_extent": temporal, "rows_or_dimensions": rows,
        "validation_status": status, "parent_files": parents,
        "transformation_command": command, "retrieved_at": utc_now(),
        "http_last_modified": headers.get("Last-Modified", ""),
        "http_etag": headers.get("ETag", ""),
    }, "path")


def status_update(source_id: str, state: str, detail: str, **extra: Any) -> None:
    path = ROOT / "metadata/status.json"
    values = json.loads(path.read_text()) if path.exists() else {}
    if state == "discovered" and values.get(source_id, {}).get("acquisition_status") in {"downloaded", "verified", "partial", "manual_required", "access_denied"}:
        return
    values[source_id] = {"acquisition_status": state, "detail": detail, "updated_at": utc_now(), **extra}
    atomic_json(path, values)
