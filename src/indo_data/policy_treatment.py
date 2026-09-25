from __future__ import annotations

from datetime import date
import json
import re
from pathlib import Path

import pandas as pd
import requests
import yaml
from pypdf import PdfReader

from .metadata import ROOT, atomic_json, register, status_update, utc_now, verify_manifest_entry


def possible_treatment_status(year: int, designation: date | None, termination: date | None, *, complete_registry: bool = False) -> str:
    """Conservative status; a year-only event must not be coerced to a date."""
    if designation and designation.year < year and (termination is None or termination.year > year):
        return "treated"
    if designation and designation.year == year:
        return "unknown"
    if termination and termination.year == year:
        return "unknown"
    if complete_registry and designation and designation.year > year:
        return "not_treated"
    return "unknown"


KEK_FIELDS = ("xid", "slug", "title", "address", "latitude", "longitude", "category", "legalBasis", "developer", "area")


def fetch_kek_details(client: requests.Session, pages: list[str], folder: Path) -> int:
    folder.mkdir(parents=True, exist_ok=True)
    count = 0
    for url in pages:
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        target = folder / f"{slug}.json"
        if target.exists():
            record = json.loads(target.read_text())
            if record.get("fields", {}).get("slug") != slug or record.get("source_page") != url:
                raise ValueError(f"Existing official KEK record does not match source page: {target}")
            verify_manifest_entry(target)
            count += 1
            continue
        response = client.get(url, timeout=30)
        response.raise_for_status()
        if "html" not in response.headers.get("Content-Type", "").lower():
            raise ValueError(f"Official KEK page not HTML: {url}")
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response.text)
        if not match:
            raise ValueError(f"No embedded official KEK data: {url}")
        page = json.loads(match.group(1))
        queries = page["props"]["pageProps"]["initialState"]["sez-regions"]["queries"]
        items = [item["data"]["data"] for item in queries.values() if item.get("endpointName") == "getDetailSezRegions" and item.get("data", {}).get("success")]
        if len(items) != 1 or items[0].get("slug") != slug:
            raise ValueError(f"KEK zone detail mismatch: {url}")
        record = {"source_page": url, "retrieved_at": utc_now(), "extraction_method": "official Next.js embedded state; signed asset URLs excluded", "fields": {field: items[0].get(field) for field in KEK_FIELDS}}
        atomic_json(target, record)
        register(target, "kek_official_registry", "JSON", rows="1", command=f"GET {url}; extract getDetailSezRegions fields", headers=dict(response.headers))
        count += 1
    status_update("kek_official_registry", "partial", f"{count} official zone detail pages acquired; national list not established")
    return count


def process_kek(folder: Path, snapshot: str) -> dict:
    rows = []
    for path in sorted(folder.glob("kek-*.json")):
        item = json.loads(path.read_text())
        fields = item["fields"]
        rows.append({"zone_id": fields["xid"], "name_original": fields["title"], "slug": fields["slug"], "sector_original": fields["category"], "listed_status": "listed_on_official_site", "designation_instrument_text": fields["legalBasis"], "designation_date": "", "legal_effective_date": "", "operational_start_date": "", "geometry_status": "unverified", "current_reference_latitude": fields["latitude"], "current_reference_longitude": fields["longitude"], "area_text": fields["area"], "source_url": item["source_page"], "review_status": "partial_registry; legal_and_geometry_review_required"})
    if not rows:
        raise ValueError("No official KEK detail records")
    frame = pd.DataFrame(rows)
    if frame.zone_id.duplicated().any():
        raise ValueError("Duplicate KEK zone IDs")
    output = ROOT / "data/processed/policy_treatment" / snapshot
    output.mkdir(parents=True, exist_ok=True)
    target = output / "kek_registry.csv"
    frame.to_csv(target, index=False)
    register(target, "kek_official_registry", "CSV", rows=str(len(frame)), parents=str(folder.relative_to(ROOT)), command="python -m indo_data process --all")
    status_update("kek_official_registry", "partial", "Official KEK detail pages verified; registry incomplete, no legal dates or polygons", rows=len(frame))
    return {"rows": len(frame)}


def process_kapet_claims(snapshot: str) -> dict:
    claims = yaml.safe_load((ROOT / "config/policy_claims.yaml").read_text())
    place_claims = yaml.safe_load((ROOT / "config/policy_places.yaml").read_text())["places"]
    if len({item["id"] for item in place_claims}) != len(place_claims):
        raise ValueError("Duplicate KAPET place claim IDs")
    zones = pd.DataFrame(claims["kapet_zones"])
    if zones.zone_id.duplicated().any():
        raise ValueError("Duplicate KAPET IDs")
    zones["geometry_status"] = "unknown"
    zones["treated_status"] = "unknown"
    zones["legal_effective_date_text"] = ""
    zones["incentive_availability_date_text"] = ""
    zones["operational_start_date_text"] = ""
    zones["termination_date_text"] = ""
    output = ROOT / "data/processed/policy_treatment" / snapshot
    output.mkdir(parents=True, exist_ok=True)
    registry = output / "kapet_registry.csv"
    zones.to_csv(registry, index=False)
    register(registry, "official_kapet_decrees", "CSV", rows=str(len(zones)), parents="config/policy_claims.yaml", command="python -m indo_data process --all")
    events = pd.DataFrame(claims["kapet_programme_events"])
    event_path = output / "kapet_legal_events.csv"
    events.to_csv(event_path, index=False)
    register(event_path, "official_kapet_decrees", "CSV", rows=str(len(events)), parents="config/policy_claims.yaml", command="python -m indo_data process --all")
    place_path = output / "kapet_place_claims.csv"
    pd.DataFrame(place_claims).to_csv(place_path, index=False)
    register(place_path, "official_kapet_decrees", "CSV", rows=str(len(place_claims)), parents="config/policy_places.yaml", command="python -m indo_data process --all")
    evidence = []
    for record in claims["kapet_zones"] + claims["kapet_programme_events"]:
        entity = record.get("zone_id") or record.get("event_id")
        evidence.append({"evidence_id": "e_" + entity, "entity_id": entity, "claim_field": "designation" if "zone_id" in record else "programme_event", "extracted_value": record.get("designation_instrument") or record.get("instrument"), "source_id": "official_kapet_decrees", "url": record["source_url"], "page_article_table": record["evidence_locator"], "supporting_excerpt": record["supporting_excerpt"], "extraction_method": "manual transcription of official indexed page/PDF text", "confidence": "medium" if "title_verified" in record["review_status"] else "high_for_cited_text_only", "review_status": record["review_status"]})
    for place in place_claims:
        evidence.append({"evidence_id": "e_place_" + place["id"], "entity_id": place["zone_id"], "claim_field": "named_place_" + place["scope"], "extracted_value": place["name"], "source_id": "official_kapet_decrees", "url": place["url"], "page_article_table": place["locator"], "supporting_excerpt": place["note"], "extraction_method": "manual transcription of official decree article", "confidence": "high_for_named_place_only", "review_status": "annex_boundary_unavailable"})
    evidence_path = ROOT / "metadata/evidence.csv"
    pd.DataFrame(evidence).to_csv(evidence_path, index=False)
    policy_evidence = output / "policy_evidence.csv"
    pd.DataFrame(evidence).to_csv(policy_evidence, index=False)
    register(policy_evidence, "official_kapet_decrees", "CSV", rows=str(len(evidence)), parents="config/policy_claims.yaml", command="python -m indo_data process --all")
    review = zones[["zone_id", "name_original", "review_status", "source_url"]].copy()
    review_path = output / "policy_review_queue.csv"
    review.to_csv(review_path, index=False)
    register(review_path, "official_kapet_decrees", "CSV", rows=str(len(review)), parents="config/policy_claims.yaml")
    status_update("official_kapet_decrees", "partial", "Fourteen source-backed designation instruments; named places recorded; annex and historical geometry incomplete", zones=len(zones), places=len(place_claims), programme_events=len(events))
    return {"zones": len(zones), "places": len(place_claims), "programme_events": len(events)}


def process_kapet_article(pdf: Path, snapshot: str) -> dict:
    reader = PdfReader(pdf)
    matches = [(index + 1, page.extract_text()) for index, page in enumerate(reader.pages) if "Data will be made available on request." in page.extract_text()]
    if len(matches) != 1:
        raise ValueError("Published KAPET article data availability statement absent or ambiguous")
    page, _ = matches[0]
    record = {
        "evidence_id": "kapet_article_data_availability_2025",
        "entity_id": "rothenberg_wang_chari_2025",
        "claim_field": "data_availability_statement",
        "extracted_value": "available on request; no open replication geometry established",
        "source_id": "rothenberg_wang_chari_2025",
        "url": "https://doi.org/10.1016/j.jdeveco.2025.103503",
        "page_article_table": f"published PDF page {page}, Data availability",
        "supporting_excerpt": "Data will be made available on request.",
        "extraction_method": "native PDF text from university repository copy of published article",
        "confidence": "high_for_statement_only",
        "review_status": "no_replication_geometry_acquired",
    }
    evidence_path = ROOT / "metadata/evidence.csv"
    old = pd.read_csv(evidence_path).to_dict("records") if evidence_path.exists() else []
    old = [item for item in old if item["evidence_id"] != record["evidence_id"]]
    pd.DataFrame(old + [record]).to_csv(evidence_path, index=False)
    output = ROOT / "data/processed/policy_treatment" / snapshot
    output.mkdir(parents=True, exist_ok=True)
    target = output / "article_data_availability.csv"
    pd.DataFrame([record]).to_csv(target, index=False)
    register(target, record["source_id"], "CSV", rows="1", parents=str(pdf.relative_to(ROOT)), command="python -m indo_data process --all")
    status_update(record["source_id"], "verified", f"Published PDF reopened; data availability statement on page {page}: available on request")
    return {"page": page}
