from __future__ import annotations

import argparse
import csv
import json
import logging
import shutil
import sys
from pathlib import Path

import geopandas as gpd
import yaml

from .arcgis import fetch_layer
from .coast_bathymetry import inspect_raster, process_coast
from .download import checked_json, session, stream_file
from .grid import grid_status
from .gebco import fetch_gebco, process_gebco
from .metadata import ROOT, atomic_json, register, relative, status_update, utc_now
from .osm_policy import fetch_osm_policy, process_osm_policy
from .peatland import inspect_peat_raster, process_government_peat
from .policy_treatment import fetch_kek_details, process_kek, process_kapet_claims, process_kapet_article
from .validate import run_validation
from .port_activity import process_daily, process_points
from .ports_historical import process_big, process_iaph_evidence

LOG = logging.getLogger("indo_data")


def settings() -> tuple[dict, dict]:
    project = yaml.safe_load((ROOT / "config/project.yaml").read_text())
    sources = yaml.safe_load((ROOT / "config/sources.yaml").read_text())
    return project, sources


def snapshot_folder(source_id: str, snapshot: str) -> Path:
    return ROOT / "data/raw" / source_id / snapshot


def newest_folder(source_id: str) -> Path | None:
    folders = sorted((ROOT / "data/raw" / source_id).glob("*"))
    folders = [path for path in folders if path.is_dir()]
    return folders[-1] if folders else None


def discover() -> None:
    project, sources = settings()
    client = session(project["http_retries"])
    rows = []
    for key, source in sources.items():
        row = {"source_id": source["id"], "group": key, "title": source["title"], "publisher": source["publisher"], "landing_url": source["landing_url"], "verified_download_or_service_url": source.get("download_url") or source.get("layer_url") or source.get("metadata_url") or (source.get("verified_detail_pages") or [""])[0], "version": "", "retrieval_timestamp": utc_now(), "coverage_dates": "", "spatial_resolution_or_scale": "", "crs": "", "units_or_classes": "", "nodata": "", "license": "", "citation": "", "access_method": "", "intended_use": key, "download_permission": "unreviewed", "analysis_permission": "unreviewed", "redistribution_permission": "unreviewed"}
        if key in {"port_activity", "port_points", "big_ports", "government_peat", "historical_port_evidence", "kek", "kapet_article"}:
            row.update(download_permission="public endpoint accessed", analysis_permission="source terms need review", redistribution_permission="not established")
        elif key in {"kapet_law", "kapet_claims"}:
            row.update(download_permission="official PDFs indexed; some shell downloads time out", analysis_permission="legal facts with article citation", redistribution_permission="not established")
        elif key == "peatland":
            row.update(download_permission="guest book and terms review required", analysis_permission="research/education terms; exact product review required", redistribution_permission="restricted; authorization review required")
        elif key == "boundary":
            row.update(download_permission="public API", analysis_permission="ODbL 1.0 conditions", redistribution_permission="ODbL obligations apply")
        elif key == "coast":
            row.update(download_permission="public ZIP", analysis_permission="ODbL conditions", redistribution_permission="ODbL obligations apply")
        elif key == "gebco":
            row.update(download_permission="public official subset", analysis_permission="public domain with attribution", redistribution_permission="attribution/disclaimer conditions")
        elif key == "osm_policy":
            row.update(download_permission="public dated archives", analysis_permission="ODbL conditions", redistribution_permission="ODbL obligations apply")
        if key == "kapet_article":
            row.update(download_permission="public repository PDF", analysis_permission="article CC BY 4.0; underlying data separate", redistribution_permission="article CC BY 4.0 attribution; underlying data not established")
        try:
            if "layer_url" in source:
                url = source["layer_url"] + ("/1" if key == "big_ports" else "")
                meta, _ = checked_json(client, url, params={"f": "json"}, timeout=project["http_timeout_s"])
                if "fields" not in meta:
                    raise ValueError("No fields in ArcGIS layer")
                row["version"] = str(meta.get("editingInfo", {}).get("dataLastEditDate") or meta.get("serviceItemId") or "")
                row["crs"] = str((meta.get("spatialReference") or meta.get("extent", {}).get("spatialReference") or {}).get("latestWkid", ""))
                row["access_method"] = "ArcGIS REST"
                status_update(source["id"], "discovered", "Layer metadata verified")
            elif key == "boundary":
                meta, _ = checked_json(client, source["metadata_url"], timeout=project["http_timeout_s"])
                row["version"] = str(meta.get("boundaryID", ""))
                row["coverage_dates"] = str(meta.get("boundaryYearRepresented", ""))
                row["license"] = str(meta.get("boundaryLicense", ""))
                row["verified_download_or_service_url"] = meta.get("gjDownloadURL", "")
                row["access_method"] = "geoBoundaries API"
                status_update(source["id"], "discovered", "API metadata and GeoJSON link verified")
            elif key == "peatland":
                row["version"] = "V3 (platform label)"
                row["spatial_resolution_or_scale"] = "approximately 236 m (platform statement)"
                row["units_or_classes"] = "peat extent; legend review required"
                row["license"] = "research/education use, no redistribution or modification without authorization; review full terms"
                row["access_method"] = "guest book and terms review"
                status_update(source["id"], "manual_required", "CIFOR guest book and terms require human action")
            elif key == "gebco":
                row["version"] = "GEBCO_2026"
                row["spatial_resolution_or_scale"] = "15 arc-second"
                row["units_or_classes"] = "signed elevation m; TID categorical"
                row["access_method"] = "CEDA OPeNDAP regional subset"
                row["verified_download_or_service_url"] = source["elevation_opendap_url"]
                status_update(source["id"], "discovered", "Official elevation and TID OPeNDAP endpoints and schema verified")
            elif key == "coast":
                response = client.head(source["download_url"], timeout=project["http_timeout_s"], allow_redirects=True)
                response.raise_for_status()
                row["version"] = response.headers.get("Last-Modified", "")
                row["license"] = "ODbL; © OpenStreetMap contributors"
                row["access_method"] = "ZIP download"
                status_update(source["id"], "discovered", f"ZIP HEAD verified; {response.headers.get('Content-Length', 'unknown')} bytes")
            elif key == "historical_port_evidence":
                row["version"] = "June 1996"
                row["coverage_dates"] = "1991/1995"
                row["access_method"] = "PDF download"
                status_update(source["id"], "discovered", "Dated PDF URL verified")
            elif key == "kapet_article":
                meta, _ = checked_json(client, source["metadata_url"], timeout=project["http_timeout_s"])
                if not any(item.get("download_url") == source["download_url"] and item.get("size", 0) > 0 for item in meta.get("files", [])):
                    raise ValueError("Published article file missing from university repository metadata")
                row["version"] = str(meta.get("version", ""))
                row["license"] = str(meta.get("license", {}).get("name", ""))
                row["citation"] = source["doi"]
                row["access_method"] = "University repository PDF"
                status_update(source["id"], "discovered", "Published article PDF and repository metadata verified")
            elif key == "osm_policy":
                row["version"] = source["version"]
                row["verified_download_or_service_url"] = ";".join(item["url"] for item in source["regions"].values())
                row["license"] = source["license"]
                row["access_method"] = "dated Geofabrik GeoPackage ZIP archives"
                row["crs"] = "source archive CRS; processed EPSG:4326"
                row["coverage_dates"] = "modern OSM snapshot, not 1990s territory"
                status_update(source["id"], "discovered", "Six dated Geofabrik regional GeoPackage URLs identified")
            else:
                status_update(source["id"], "discovered", "Official landing/document link identified; details under review")
        except Exception as exc:
            prior = json.loads((ROOT / "metadata/status.json").read_text()).get(source["id"], {}) if (ROOT / "metadata/status.json").exists() else {}
            if prior.get("acquisition_status") not in {"downloaded", "verified", "partial", "manual_required", "access_denied"}:
                status_update(source["id"], "failed", str(exc))
        current_status_path = ROOT / "metadata/status.json"
        if current_status_path.exists():
            current = json.loads(current_status_path.read_text()).get(source["id"], {})
            if key == "port_activity" and current.get("first_observed_date"):
                row["coverage_dates"] = current["first_observed_date"] + "/" + current["last_observed_date"]
            if key == "government_peat" and current.get("bounds"):
                row["spatial_resolution_or_scale"] = "regional public service; native map scale unverified"
            if key == "gebco":
                row["coverage_dates"] = "2026 grid release; source survey dates heterogeneous"
                row["crs"] = "EPSG:4326"
                row["license"] = "public domain with attribution/disclaimer conditions"
                row["citation"] = "GEBCO Bathymetric Compilation Group (2026), doi:10.5285/4f68d5c7-45eb-f999-e063-7086abc036fa"
        rows.append(row)
    path = ROOT / "metadata/source_catalog.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fetch(selected: str | None = None) -> list[str]:
    project, sources = settings()
    client = session(project["http_retries"])
    date = project["as_of_date"]
    max_bytes = int(project["max_single_download_gb"] * 1024 ** 3)
    failures = []
    if selected == "osm_policy":
        source = sources["osm_policy"]
        try:
            fetch_osm_policy(client, source, project)
        except Exception as exc:
            failures.append(f"OSM policy: {exc}")
            status_update(source["id"], "failed", str(exc))
        return failures
    if selected == "gebco":
        source = sources["gebco"]
        try:
            folder = snapshot_folder(source["id"], date)
            fetch_gebco(source, project["coast_context_bbox"], folder, block_rows=project["gebco_block_rows"], max_single_bytes=max_bytes)
        except Exception as exc:
            failures.append(f"GEBCO: {exc}")
            status_update(source["id"], "failed", str(exc))
        return failures
    if selected == "kek":
        source = sources["kek"]
        try:
            fetch_kek_details(client, source["verified_detail_pages"], snapshot_folder(source["id"], date))
        except Exception as exc:
            failures.append(f"KEK: {exc}")
            status_update(source["id"], "failed", str(exc))
        return failures
    if selected == "historical_port_evidence":
        source = sources["historical_port_evidence"]
        try:
            folder = snapshot_folder(source["id"], date)
            stream_file(client, source["download_url"], folder / "ports_and_harbors_1996_06.pdf", source["id"], max_bytes=max_bytes, expected_kind="pdf")
            status_update(source["id"], "downloaded", "Dated 1996 industry-association document stored; Table 3.3 needs extraction QA")
        except Exception as exc:
            failures.append(f"historical port evidence: {exc}")
            status_update(source["id"], "failed", str(exc))
        return failures
    if selected == "kapet_article":
        source = sources["kapet_article"]
        try:
            folder = snapshot_folder(source["id"], date)
            meta, headers = checked_json(client, source["metadata_url"], timeout=project["http_timeout_s"])
            from .download import save_json
            save_json(folder / "repository_metadata.json", meta, source["id"], command=f"GET {source['metadata_url']}", headers=headers)
            stream_file(client, source["download_url"], folder / "published_article.pdf", source["id"], max_bytes=max_bytes, expected_kind="pdf")
            status_update(source["id"], "downloaded", "Published KAPET article and repository metadata acquired; data availability statement under review")
        except Exception as exc:
            failures.append(f"KAPET article: {exc}")
            status_update(source["id"], "failed", str(exc))
        return failures
    if selected == "government_peat":
        source = sources["government_peat"]
        try:
            folder = snapshot_folder(source["id"], date)
            fetch_layer(client, source["layer_url"], source["id"], folder, "1=1", batch_size=project["arcgis_batch_size"], timeout=project["http_timeout_s"])
            value, headers = checked_json(client, source["layer_url"] + "/query", params={"f": "geojson", "where": "1=1", "outFields": "*", "returnGeometry": "true", "outSR": "4326"}, timeout=project["http_timeout_s"])
            expected = json.loads((folder / "ids.json").read_text())["count"]
            if value.get("type") != "FeatureCollection" or len(value.get("features", [])) != expected:
                raise ValueError("Government peat GeoJSON count/format mismatch")
            from .download import save_json
            save_json(folder / "features.geojson", value, source["id"], command=f"GET {source['layer_url']}/query f=geojson", headers=headers)
        except Exception as exc:
            failures.append(f"government peat: {exc}")
            status_update(source["id"], "failed", str(exc))
        return failures
    if selected == "big_ports":
        source = sources["big_ports"]
        for layer_id in source["layer_ids"]:
            try:
                url = source["layer_url"] + f"/{layer_id}"
                folder = snapshot_folder(source["id"], date) / f"layer_{layer_id}"
                fetch_layer(client, url, f"{source['id']}_{layer_id}", folder, "1=1", batch_size=project["arcgis_batch_size"], timeout=project["http_timeout_s"])
            except Exception as exc:
                failures.append(f"big layer {layer_id}: {exc}")
                status_update(f"{source['id']}_{layer_id}", "failed", str(exc))
        return failures
    boundary = sources["boundary"]
    try:
        meta, headers = checked_json(client, boundary["metadata_url"], timeout=project["http_timeout_s"])
        folder = snapshot_folder(boundary["id"], date + "_" + str(meta["boundaryID"]))
        folder.mkdir(parents=True, exist_ok=True)
        from .download import save_json
        save_json(folder / "api_metadata.json", meta, boundary["id"], command=f"GET {boundary['metadata_url']}", headers=headers)
        stream_file(client, meta["gjDownloadURL"], folder / "adm0.geojson", boundary["id"], max_bytes=max_bytes, expected_kind="geojson")
        status_update(boundary["id"], "downloaded", "API metadata and native GeoJSON stored", boundary_year=meta.get("boundaryYearRepresented"), license=meta.get("boundaryLicense"))
    except Exception as exc:
        failures.append(f"boundary: {exc}")
        status_update(boundary["id"], "failed", str(exc))
    for key in ("port_activity", "port_points"):
        source = sources[key]
        try:
            meta, _ = checked_json(client, source["layer_url"], params={"f": "json"}, timeout=project["http_timeout_s"])
            version = str(meta.get("editingInfo", {}).get("dataLastEditDate") or "unknown")
            folder = snapshot_folder(source["id"], date + "_" + version)
            where = "ISO3='IDN' AND date >= DATE '" + project["port_activity_requested_start"] + "'" if key == "port_activity" else "ISO3='IDN'"
            fetch_layer(client, source["layer_url"], source["id"], folder, where, batch_size=project["arcgis_batch_size"], timeout=project["http_timeout_s"])
        except Exception as exc:
            failures.append(f"{key}: {exc}")
            status_update(source["id"], "failed", str(exc))
    source = sources["big_ports"]
    for layer_id in source["layer_ids"]:
        try:
            url = source["layer_url"] + f"/{layer_id}"
            folder = snapshot_folder(source["id"], date) / f"layer_{layer_id}"
            fetch_layer(client, url, f"{source['id']}_{layer_id}", folder, "1=1", batch_size=project["arcgis_batch_size"], timeout=project["http_timeout_s"])
        except Exception as exc:
            failures.append(f"big layer {layer_id}: {exc}")
            status_update(f"{source['id']}_{layer_id}", "failed", str(exc))
    failures.extend(fetch("government_peat"))
    failures.extend(fetch("gebco"))
    failures.extend(fetch("kek"))
    failures.extend(fetch("historical_port_evidence"))
    failures.extend(fetch("kapet_article"))
    failures.extend(fetch("osm_policy"))
    source = sources["coast"]
    try:
        folder = snapshot_folder(source["id"], date)
        stream_file(client, source["download_url"], folder / "coastlines-split-4326.zip", source["id"], max_bytes=max_bytes, expected_kind="zip", timeout=project["http_timeout_s"])
        status_update(source["id"], "downloaded", "Original processed OSM coastline ZIP stored")
    except Exception as exc:
        failures.append(f"coast: {exc}")
        status_update(source["id"], "failed", str(exc))
    source = sources["kapet_law"]
    successes = 0
    legal_client = session(0)
    for document in source["verified_documents"]:
        try:
            folder = snapshot_folder(source["id"], date)
            stream_file(legal_client, document["url"], folder / (document["id"] + ".pdf"), source["id"], max_bytes=max_bytes, expected_kind="pdf", timeout=12)
            successes += 1
        except Exception as exc:
            failures.append(f"{document['id']}: {exc}")
            if successes == 0:
                break  # Same official host is likely inaccessible; continue other tasks.
    status_update(source["id"], "partial" if successes else "failed", f"{successes}/{len(source['verified_documents'])} official PDFs acquired; registry and boundaries pending")
    return failures


def process() -> list[str]:
    project, sources = settings()
    failures = []
    folder = newest_folder(sources["boundary"]["id"])
    if folder and (folder / "adm0.geojson").exists():
        try:
            frame = gpd.read_file(folder / "adm0.geojson")
            if frame.empty or frame.crs is None or not frame.geometry.is_valid.all():
                raise ValueError("Invalid ADM0 geometry")
            target = ROOT / "data/processed/boundary" / project["as_of_date"] / "indonesia_adm0.gpkg"
            target.parent.mkdir(parents=True, exist_ok=True)
            frame.to_file(target, driver="GPKG", layer="indonesia_adm0")
            register(target, sources["boundary"]["id"], "GeoPackage", extent=str(tuple(frame.total_bounds)), rows=str(len(frame)), parents=relative(folder / "adm0.geojson"), command="python -m indo_data process --all")
            status_update(sources["boundary"]["id"], "verified", "ADM0 GeoJSON reopened and valid; national selection boundary", features=len(frame), bounds=tuple(frame.total_bounds))
        except Exception as exc:
            failures.append(f"boundary process: {exc}")
    for key, processor in (("port_activity", process_daily), ("port_points", process_points)):
        folder = newest_folder(sources[key]["id"])
        if folder and list(folder.glob("batch_*.json")):
            try:
                processor(folder, project["as_of_date"])
            except Exception as exc:
                failures.append(f"{key} process: {exc}")
    big_root = newest_folder(sources["big_ports"]["id"])
    if big_root:
        folders = {layer_id: big_root / f"layer_{layer_id}" for layer_id in sources["big_ports"]["layer_ids"] if list((big_root / f"layer_{layer_id}").glob("batch_*.json"))}
        if folders:
            try:
                process_big(folders, project["as_of_date"])
            except Exception as exc:
                failures.append(f"BIG process: {exc}")
    folder = newest_folder(sources["coast"]["id"])
    if folder and (folder / "coastlines-split-4326.zip").exists():
        try:
            process_coast(folder / "coastlines-split-4326.zip", project["coast_context_bbox"], project["as_of_date"])
        except Exception as exc:
            failures.append(f"coast process: {exc}")
    folder = newest_folder(sources["government_peat"]["id"])
    if folder and (folder / "features.geojson").exists():
        try:
            process_government_peat(folder / "features.geojson", project["as_of_date"])
        except Exception as exc:
            failures.append(f"government peat process: {exc}")
    folder = newest_folder(sources["gebco"]["id"])
    if folder and all((folder / f"gebco_2026_{kind}_regional.nc").exists() for kind in ("elevation", "tid")):
        try:
            process_gebco(folder, project["as_of_date"])
        except Exception as exc:
            failures.append(f"GEBCO process: {exc}")
    folder = newest_folder(sources["kek"]["id"])
    if folder and list(folder.glob("kek-*.json")):
        try:
            process_kek(folder, project["as_of_date"])
        except Exception as exc:
            failures.append(f"KEK process: {exc}")
    try:
        process_kapet_claims(project["as_of_date"])
    except Exception as exc:
        failures.append(f"KAPET claims process: {exc}")
    folder = newest_folder(sources["osm_policy"]["id"])
    if folder and len(list(folder.glob("*-free.gpkg.zip"))) == 6:
        try:
            process_osm_policy(folder, project["as_of_date"])
        except Exception as exc:
            failures.append(f"OSM policy process: {exc}")
    folder = newest_folder(sources["kapet_article"]["id"])
    if folder and (folder / "published_article.pdf").exists():
        try:
            process_kapet_article(folder / "published_article.pdf", project["as_of_date"])
        except Exception as exc:
            failures.append(f"KAPET article process: {exc}")
    folder = newest_folder(sources["historical_port_evidence"]["id"])
    if folder and (folder / "ports_and_harbors_1996_06.pdf").exists():
        try:
            process_iaph_evidence(folder / "ports_and_harbors_1996_06.pdf", project["as_of_date"])
        except Exception as exc:
            failures.append(f"historical port evidence process: {exc}")
    return failures


def ingest_manual(theme: str, path: Path) -> None:
    path = path.resolve()
    manual_root = (ROOT / "data/manual" / theme).resolve()
    if not path.is_relative_to(manual_root):
        raise ValueError(f"Manual import must be staged under {manual_root}")
    if not path.is_file():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix in (".tif", ".tiff"):
        info = inspect_peat_raster(path) if theme == "peatland" else inspect_raster(path)
        register(path, "manual_" + theme, "GeoTIFF", extent=str(info["bounds"]), rows=f"{info['width']}x{info['height']}", status="verified", command="python -m indo_data ingest-manual")
    elif suffix == ".pdf":
        from .download import verify_file
        verify_file(path, "pdf")
        register(path, "manual_" + theme, "PDF", command="python -m indo_data ingest-manual")
    else:
        raise ValueError("Manual importer currently accepts GeoTIFF or PDF; archives need inspected extraction")
    status_update("manual_" + theme, "verified", f"Imported and reopened {relative(path)}")


def validate() -> list[str]:
    project, _ = settings()
    checks, failures = run_validation(project["as_of_date"])
    report = ROOT / "reports/qa_report.md"
    report.write_text("# Offline QA report\n\n" + "\n".join(f"- {item}" for item in checks) + f"\n\nFailures: {len(failures)}.\n" + "\n".join(f"- {failure}" for failure in failures) + "\n")
    return failures


def report() -> None:
    from .qa_figures import create_figures
    project, _ = settings()
    figures = create_figures(project["as_of_date"])
    location_review = ROOT / "data/processed/policy_treatment" / project["as_of_date"] / "policy_location_review.csv"
    queue_path = ROOT / "reports/review_queue.csv"
    if location_review.exists() and queue_path.exists():
        with queue_path.open(newline="") as handle:
            queue = [row for row in csv.DictReader(handle) if not row["item_id"].startswith("policy_place_")]
        for row in queue:
            if row["item_id"] == "kapet_laws":
                row["issue"] = "Designation articles transcribed; annex maps, timing and historical boundaries unresolved"
        with location_review.open(newline="") as handle:
            for place in csv.DictReader(handle):
                if place["status"] == "modern_polygon_proxy":
                    continue
                queue.append({"item_id": "policy_place_" + place["claim_id"], "theme": "policy_treatment", "priority": "high" if place["status"] in {"ambiguous_osm_name", "ambiguous_site_polygons"} else "medium", "issue": f"{place['name']}: {place['status']}; {place['review_note']}", "action": "Review official annex and present-day OSM identity; retain location proxy role", "source_url": place["legal_url"], "status": "open"})
        with queue_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["item_id", "theme", "priority", "issue", "action", "source_url", "status"])
            writer.writeheader()
            writer.writerows(queue)
    status_file = ROOT / "metadata/status.json"
    status = json.loads(status_file.read_text()) if status_file.exists() else {}
    policy_stats = status.get("geofabrik_osm_policy", {})
    lines = ["# Acquisition report", "", "Run date: 2026-09-25. Scope: five research groups plus ADM0 and dated OSM policy-location support. Status is based on the files and checks below.", "", "| Source | Acquisition | Detail |", "|---|---|---|"]
    for source_id, item in sorted(status.items()):
        lines.append(f"| {source_id} | {item['acquisition_status']} | {item['detail'].replace('|', '/')} |")
    manifest = ROOT / "metadata/file_manifest.csv"
    if manifest.exists():
        with manifest.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        total = sum(int(item["bytes"]) for item in rows)
        lines += ["", f"Manifest: {len(rows)} files, {total:,} bytes (raw and derived; checksums in metadata/file_manifest.csv).", ""]
    lines += [
        "## Group results", "",
        "### Peatland — partial; preferred raster requires manual access", "",
        "- Obtained: BIG/Kementerian Pertanian *Peta Lahan Gambut* public MapServer layer 6, 146 valid soil polygons in a Kalimantan-only extent (108.86–118.58°E, 3.46°S–4.07°N). Raw ArcGIS responses and `data/processed/peatland/2026-09-25/big_peta_lahan_gambut_partial.gpkg` are recorded in the manifest.",
        "- Usable role: supplementary regional peat-soil evidence. Outside these polygons and the service extent remains unknown. This does not yield a national peat or non-peat mask, and the map has no verified 1992 vintage.",
        "- CIFOR Global Wetlands V3 peat-extent raster was not acquired because its guest book and terms require human review. See `docs/manual_actions.md`; inspect the exact product legend and rights before any canonical mask.", "",
        "### Port activity — acquired and validated for contemporary use", "",
        "- Obtained: IMF PortWatch `Daily_Ports_Data` Indonesia extract, 284,618 unique port-date records across 101 ports, actually observed 2019-01-01 through 2026-09-18; 101 companion current points. Outputs are daily (284,618 rows), monthly (9,393), and annual (808) Parquet plus GeoPackage under `data/processed/port_activity/2026-09-25/`.",
        "- Validation: ArcGIS IDs/counts and edit timestamp reconciled; no duplicate keys or missing point joins; month/year calendar coverage and missingness checked. Port calls and shipment estimates retain publisher meanings and units. Incomplete periods are flagged, not extrapolated.",
        "- Usable role: contemporary activity only. It does not measure 1992–2000 port throughput; points are not assigned historical geometry.", "",
        "### Historical ports — current inventory plus limited dated evidence", "",
        "- Obtained: BIG/Kemenhub public ports layer 1 (527 points) and special terminals layer 3 (1,978), 2,505 current points total. The year-field audit found only two plausible values in each of three fields for public ports; the other 525 values were `0`. All 1,978 terminal entries were `-` in each field. The field meanings are not enough to establish openings.",
        "- Obtained: International Association of Ports and Harbors, *Ports and Harbors*, June 1996, PDF page 21 / printed page 19, Table 3.3. Positive 1991–1995 container entries document seven named ports in 1992 and 1995. Outputs: 35 event rows and 203 port-year rows through 2020; all post-1995 presence is `unknown`. Quantities were withheld because PDF text extraction has errors.",
        "- Usable role: seven evidence-supported historical presences without historical coordinates; current BIG points are separate location proxies. The 2000 reference year, identity crosswalk, location stability, and national completeness need review.", "",
        "### Coast and bathymetry — acquired and validated as current geography", "",
        "- Obtained: processed OSM coastline ZIP snapshot dated 2026-09-25 and 22,086 valid clipped regional lines in `regional_coastline.gpkg`; it includes neighbouring coasts and has no reviewed country segment labels.",
        "- Obtained: GEBCO_2026 official CEDA OPeNDAP regional elevation and Type Identifier subsets, both 5,040 × 12,000 native 15 arc-second cells over 93–143°E, 13°S–8°N. Raw NetCDF and source metadata plus separate north-up GeoTIFFs are retained. Elevation is signed metres; TID is categorical. Extents, CRS, shape, and sampled values were checked.",
        "- Usable role: current coast and candidate natural-geography inputs. Reclamation, dredging, survey vintages, TID quality, and coastline country attribution need interpretation before a historical harbour instrument is claimed.", "",
        "### Policy treatment — partial evidence; no verified treatment geometry", "",
        "- KAPET: 14 official designation instruments and 70 named whole units, partial units, districts and islands are transcribed with article references in `kapet_registry.csv` and `kapet_place_claims.csv`. The 1998 Benaviq designation names places in historical Timor Timur, outside current Indonesia. Missing decree maps and administrative changes remain explicit. `treated_status` and historical geometry remain `unknown`.",
        f"- Dated Geofabrik OSM GeoPackages for Sumatra, Kalimantan, Sulawesi, Papua, Maluku and Nusa Tenggara (`260924` snapshot) were downloaded, checksum registered and processed. `policy_location_proxies.gpkg` has four QGIS layers: {policy_stats.get('polygons', 'unknown')} modern whole-unit KAPET polygons, {policy_stats.get('review_points', 'unknown')} KAPET review points, two KEK exact named OSM site polygon candidates, and {policy_stats.get('kek_reference_points', 'unknown')} official KEK reference points. These are current location proxies only. `policy_location_crosswalk.csv` records legal and OSM identifiers; `policy_location_review.csv` retains all 72 legal/site review rows, including unresolved ones.",
        "- KEK: two official detail records (Palu, manufacturing, PP 31/2014; Nongsa, service, PP 68/2021) are in a separate partial registry. Exact named OSM site polygons are candidates, not official boundaries. Legal effective dates and official site boundaries remain unverified. The official API requires authorization; no credentials were used.",
        "- The published 2025 KAPET evaluation PDF was acquired from the University of Sussex repository. Its Data availability statement says data will be available on request (PDF page 22); this does not establish an open replication package or usable boundary geometry. The author publication page links replication packages for other papers, but none for this article at the time checked.",
        "- Official KAPET decree article text was reviewed through indexed official PDFs, but full annex maps and some effective dates were unavailable. Import original decrees using `docs/manual_actions.md`, resolve boundaries and legal timing, and verify any subsequently obtained replication geometry before using treatment in the 1992–2020 panel.", "",
        "### Supporting boundary", "",
        "- geoBoundaries gbOpen Indonesia ADM0 GeoJSON represented year 2017, one valid multipolygon with 1,312 components. It is a national selection reference only; independent small-island completeness and historical administrative equivalence remain unverified.", "",
        "## Reproduce and review", "",
        "- Online sequence: `.venv/bin/python -m indo_data discover`, then `fetch --all`, `process --all`, `validate`, and `report`. Repeated fetches reuse unchanged local snapshots after integrity checks; changed upstream vintages are stored separately where the service supplies a version.",
        "- Offline checks: `.venv/bin/python -m indo_data validate` and `.venv/bin/python -m indo_data report`. Inspect `reports/qa_report.md`, `reports/temporal_compatibility.csv`, `reports/review_queue.csv`, `metadata/source_catalog.csv`, and `metadata/file_manifest.csv`.",
        "- QGIS styling and interpretation: `docs/qgis_gebco_policy.md`. Manual actions: `docs/manual_actions.md`. Rights review: `metadata/licenses/rights_review.md`.", "",
        "QA figures: " + (", ".join(figures) if figures else "none; no acquired geometry to plot"),
    ]
    (ROOT / "reports/acquisition_report.md").write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="indo_data")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("discover", "fetch", "process", "validate", "report", "run", "grid"):
        command = sub.add_parser(name)
        if name in ("fetch", "process", "run"):
            command.add_argument("--all", action="store_true")
        if name == "fetch":
            command.add_argument("--source", choices=["big_ports", "government_peat", "gebco", "kek", "historical_port_evidence", "kapet_article", "osm_policy"])
        if name == "grid":
            command.add_argument("--resolution", type=int, default=10000)
    manual = sub.add_parser("ingest-manual")
    manual.add_argument("--theme", choices=["peatland", "coast_bathymetry", "policy_treatment"], required=True)
    manual.add_argument("--path", type=Path, required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    failures: list[str] = []
    if args.command == "discover":
        discover()
    elif args.command == "fetch":
        failures = fetch(args.source)
    elif args.command == "process":
        failures = process()
    elif args.command == "validate":
        failures = validate()
    elif args.command == "report":
        report()
    elif args.command == "run":
        discover()
        failures = fetch()
        failures += process()
        failures += validate()
        report()
    elif args.command == "grid":
        project, _ = settings()
        if args.resolution not in project["grid_sizes_m"]:
            parser.error("Resolution must be one of the configured grid sizes")
        print(grid_status())
    elif args.command == "ingest-manual":
        ingest_manual(args.theme, args.path)
    for item in failures:
        LOG.error(item)
    return 2 if failures else 0
