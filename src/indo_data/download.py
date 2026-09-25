from __future__ import annotations

import json
import logging
import zipfile
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .metadata import ROOT, atomic_json, register, verify_manifest_entry

LOG = logging.getLogger(__name__)


def session(retries: int = 3) -> requests.Session:
    client = requests.Session()
    client.headers.update({"User-Agent": "indo-data-research/0.1 (public data acquisition)"})
    retry = Retry(total=retries, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET", "HEAD", "POST"])
    client.mount("https://", HTTPAdapter(max_retries=retry))
    return client


def checked_json(client: requests.Session, url: str, *, params: dict[str, Any] | None = None, timeout: int = 60, method: str = "GET") -> tuple[dict[str, Any], dict[str, str]]:
    response = client.request(method, url, params=params if method == "GET" else None, data=params if method == "POST" else None, timeout=timeout)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if "json" not in content_type.lower() and not response.content.lstrip().startswith((b"{", b"[")):
        raise ValueError(f"Expected JSON, got {content_type}: {url}")
    value = response.json()
    if not isinstance(value, dict) or "error" in value:
        raise ValueError(f"Invalid service response at {url}: {str(value)[:400]}")
    return value, dict(response.headers)


def save_json(path: Path, value: dict[str, Any], source_id: str, *, parent: str = "", command: str = "", headers: dict[str, str] | None = None) -> None:
    if path.exists():
        previous = json.loads(path.read_text())
        if previous != value:
            raise FileExistsError(f"Immutable raw response changed: {path}")
        verify_manifest_entry(path)
        return
    atomic_json(path, value)
    register(path, source_id, "JSON", parents=parent, command=command, headers=headers)


def stream_file(client: requests.Session, url: str, target: Path, source_id: str, *, max_bytes: int, timeout: int = 60, expected_kind: str = "zip") -> None:
    if target.exists():
        verify_file(target, expected_kind)
        verify_manifest_entry(target)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".part")
    if temp.exists():
        temp.unlink()  # No unsafe resume across an unpinned upstream version.
    with client.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        size_header = response.headers.get("Content-Length")
        if size_header and int(size_header) > max_bytes:
            raise ValueError(f"Download exceeds configured limit: {size_header} bytes")
        total = 0
        try:
            with temp.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("Download exceeded configured limit")
                    handle.write(chunk)
            verify_file(temp, expected_kind)
            temp.replace(target)
            register(target, source_id, expected_kind.upper(), headers=dict(response.headers))
        finally:
            temp.unlink(missing_ok=True)


def verify_file(path: Path, kind: str) -> None:
    if path.stat().st_size == 0:
        raise ValueError(f"Empty file: {path}")
    with path.open("rb") as handle:
        prefix = handle.read(512).lstrip().lower()
    if prefix.startswith((b"<!doctype html", b"<html")) or (kind not in ("geojson",) and prefix.startswith(b"{")):
        raise ValueError(f"Unexpected HTML/JSON content: {path}")
    if kind == "zip":
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f"Corrupt ZIP member: {bad}")
    elif kind == "pdf" and not prefix.startswith(b"%pdf"):
        raise ValueError(f"Invalid PDF: {path}")
    elif kind == "tiff" and not prefix.startswith((b"ii*\x00", b"mm\x00*", b"ii+\x00", b"mm\x00+")):
        raise ValueError(f"Invalid TIFF: {path}")
    elif kind == "geojson":
        value = json.loads(path.read_text())
        if value.get("type") != "FeatureCollection" or not value.get("features"):
            raise ValueError(f"Invalid GeoJSON feature collection: {path}")
