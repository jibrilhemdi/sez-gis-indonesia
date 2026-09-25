from __future__ import annotations

from pathlib import Path
import csv
import re

import geopandas as gpd
import pandas as pd
from pypdf import PdfReader
from shapely.geometry import Point

from .metadata import ROOT, register, status_update
from .port_activity import read_batches


def process_big(folders: dict[int, Path], snapshot: str) -> dict:
    parts = []
    stats = []
    for layer_id, folder in folders.items():
        rows = read_batches(folder)
        if not rows:
            continue
        frame = pd.DataFrame(rows)
        geoms = frame.pop("_geometry").map(lambda v: Point(v["x"], v["y"]) if isinstance(v, dict) and "x" in v and "y" in v else None)
        frame["source_layer_id"] = layer_id
        frame["facility_type"] = "public_port" if layer_id == 1 else "special_terminal"
        frame["geometry_role"] = "current_location_proxy"
        frame["geometry_vintage"] = None
        frame["location_stability"] = "unverified"
        points = gpd.GeoDataFrame(frame, geometry=geoms, crs="EPSG:4326")
        if points.geometry.isna().any() or not points.geometry.is_valid.all():
            raise ValueError(f"BIG layer {layer_id} invalid geometries")
        for field in ("thn_bng", "thn_kmb", "thn_ops"):
            if field in frame:
                values = pd.to_numeric(frame[field], errors="coerce")
                missing = frame[field].isna() | frame[field].astype(str).str.strip().isin(["", "None", "nan"])
                valid = values.between(1800, 2026)
                stats.append({"layer_id": layer_id, "field": field, "rows": len(frame), "valid_years": int(valid.sum()), "missing": int(missing.sum()), "sentinel_or_invalid": int((~missing & ~valid).sum()), "raw_values_outside_range": ";".join(str(x) for x in sorted(frame.loc[~missing & ~valid, field].astype(str).unique())[:20])})
        parts.append(points)
    if not parts:
        raise ValueError("No BIG port records")
    combined = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs="EPSG:4326")
    if combined.duplicated(["source_layer_id", "objectid"]).any():
        raise ValueError("Duplicate BIG source IDs")
    output = ROOT / "data/processed/ports_historical" / snapshot
    output.mkdir(parents=True, exist_ok=True)
    target = output / "ports_current.gpkg"
    combined.to_file(target, driver="GPKG", layer="ports_current")
    register(target, "big_kemenhub_ports", "GeoPackage", extent=str(tuple(combined.total_bounds)), rows=str(len(combined)), parents=";".join(str(f.relative_to(ROOT)) for f in folders.values()), command="python -m indo_data process --all")
    proxy = output / "ports_static_proxy.gpkg"
    combined[["source_layer_id", "objectid", "namobj", "facility_type", "geometry_role", "geometry_vintage", "location_stability", "geometry"]].to_file(proxy, driver="GPKG", layer="ports_static_proxy")
    register(proxy, "big_kemenhub_ports", "GeoPackage", extent=str(tuple(combined.total_bounds)), rows=str(len(combined)), parents=str(target.relative_to(ROOT)))
    stats_path = output / "big_year_field_audit.csv"
    pd.DataFrame(stats).to_csv(stats_path, index=False)
    register(stats_path, "big_kemenhub_ports", "CSV", rows=str(len(stats)), parents=str(target.relative_to(ROOT)))
    # Every cross-source match needs independent review; record candidates without merging.
    queue = combined[["source_layer_id", "objectid", "namobj", "facility_type"]].copy()
    queue["review_reason"] = "Opening meaning and location stability unverified; cross-source identity unresolved"
    queue_path = output / "historical_port_review_queue.csv"
    queue.to_csv(queue_path, index=False)
    register(queue_path, "big_kemenhub_ports", "CSV", rows=str(len(queue)), parents=str(target.relative_to(ROOT)))
    status_update("big_kemenhub_ports", "partial", "Current inventory verified; historical presence and geometry unresolved", rows=len(combined), year_field_audit=stats)
    return {"rows": len(combined), "year_field_audit": stats}


IAPH_NAMES = {
    "TG. PRIOK": ("hist_tanjung_priok", "Tanjung Priok"),
    "TG. PERAK": ("hist_tanjung_perak", "Tanjung Perak"),
    "BELAWAN": ("hist_belawan", "Belawan"),
    "TG, EMAS": ("hist_tanjung_emas", "Tanjung Emas"),
    "MAKASAR": ("hist_makassar", "Makassar"),
    "PALEMBANG": ("hist_palembang", "Palembang"),
    "PANJANG": ("hist_panjang", "Panjang"),
}


def evidence_presence(year: int, observed_years: set[int]) -> str:
    """A dated listing proves that year's presence only; other years stay unknown."""
    return "documented_present" if year in observed_years else "unknown"


def process_iaph_evidence(pdf: Path, snapshot: str) -> dict:
    reader = PdfReader(pdf)
    if len(reader.pages) <= 20:
        raise ValueError("IAPH PDF is shorter than the cited table page")
    page_text = reader.pages[20].extract_text()
    if "Table 3.3" not in page_text or "1991-1995" not in page_text:
        raise ValueError("IAPH table not found on PDF page 21")
    lines = page_text.splitlines()
    output = ROOT / "data/processed/ports_historical" / snapshot
    output.mkdir(parents=True, exist_ok=True)
    events = []
    annual = []
    evidence = []
    review = []
    for source_name, (port_id, standard_name) in IAPH_NAMES.items():
        matches = [line.strip() for line in lines if line.strip().lstrip(". ").startswith(source_name)]
        if len(matches) != 1:
            raise ValueError(f"Expected one IAPH table row for {source_name}, got {len(matches)}")
        tokens = re.findall(r"\d[\d,]*", matches[0])
        if len(tokens) < 5:
            raise ValueError(f"Incomplete 1991–1995 IAPH row: {source_name}")
        if any(int(token.replace(",", "")) <= 0 for token in tokens[:5]):
            raise ValueError(f"Non-positive traffic in IAPH row: {source_name}")
        evidence_id = "iaph1996_table33_" + port_id
        evidence.append({"evidence_id": evidence_id, "entity_id": port_id, "claim_field": "documented_port_presence_1991_1995", "extracted_value": source_name, "source_id": "iaph_ports_harbors_1996_06", "url": "https://www.iaphworldports.org/n-iaph/wp-content/uploads/ph/1996-5.pdf", "page_article_table": "PDF page 21, printed page 19, Table 3.3", "supporting_excerpt": matches[0][:120], "extraction_method": "native PDF text; positive year entries checked; quantities not transcribed due OCR errors", "confidence": "high_for_presence; name_crosswalk_unreviewed", "review_status": "current_source_match_and_geometry_needed"})
        for year in range(1991, 1996):
            events.append({"port_id": port_id, "original_name": source_name, "standardized_name": standard_name, "event_type": "container_traffic_reported", "event_year": year, "date_precision": "year", "reported_table_value": "", "reported_unit_note": "Quantity not transcribed due OCR errors; use original PDF for TEU values", "evidence_id": evidence_id, "geometry_role": "none", "source_parent_id": "", "confidence": "documented presence; quantity unreviewed"})
        for year in range(1992, 2021):
            presence = evidence_presence(year, set(range(1991, 1996)))
            annual.append({"port_id": port_id, "year": year, "presence_status": presence, "evidence_id": evidence_id if presence == "documented_present" else "", "geometry_role": "none", "continuity_assumption": "none"})
        review.append({"port_id": port_id, "historical_name": source_name, "standardized_name": standard_name, "first_known_present_year": 1991, "issue": "Resolve current BIG/PortWatch crosswalk and historical location; no post-1995 continuity assumed", "evidence_id": evidence_id})
    events_path = output / "port_history_events.csv"
    pd.DataFrame(events).to_csv(events_path, index=False)
    register(events_path, "iaph_ports_harbors_1996_06", "CSV", rows=str(len(events)), temporal="1991/1995", parents=str(pdf.relative_to(ROOT)), command="python -m indo_data process --all")
    presence_path = output / "port_presence_1992_2020.parquet"
    pd.DataFrame(annual).to_parquet(presence_path, index=False)
    register(presence_path, "iaph_ports_harbors_1996_06", "Parquet", rows=str(len(annual)), temporal="1992/2020", parents=str(events_path.relative_to(ROOT)), command="python -m indo_data process --all")
    review_path = output / "historical_evidence_review_queue.csv"
    pd.DataFrame(review).to_csv(review_path, index=False)
    register(review_path, "iaph_ports_harbors_1996_06", "CSV", rows=str(len(review)), parents=str(events_path.relative_to(ROOT)))
    evidence_path = ROOT / "metadata/evidence.csv"
    old = pd.read_csv(evidence_path).to_dict("records") if evidence_path.exists() else []
    old = [item for item in old if not str(item["evidence_id"]).startswith("iaph1996_")]
    pd.DataFrame(old + evidence).to_csv(evidence_path, index=False)
    status_update("iaph_ports_harbors_1996_06", "partial", "Seven ports documented in 1991–1995 table; current identity and historic geometry unresolved", ports=7, documented_reference_years=[1992, 1995], unsupported_reference_years=[2000])
    return {"ports": 7, "events": len(events), "presence_rows": len(annual)}
