"""Dated OSM extracts and explicitly modern policy-location proxies."""

from __future__ import annotations

import shutil
from pathlib import Path

import requests

from .download import save_json, stream_file
from .metadata import ROOT, status_update


def fetch_osm_policy(client: requests.Session, source: dict, project: dict) -> dict:
    """Preflight every pinned archive before downloading any of them."""
    folder = ROOT / "data/raw" / source["id"] / project["as_of_date"]
    folder.mkdir(parents=True, exist_ok=True)
    max_single = int(project["max_single_download_gb"] * 1024**3)
    max_total = int(project["max_total_download_gb"] * 1024**3)
    planned = []
    for region, entry in source["regions"].items():
        response = client.head(entry["url"], allow_redirects=True, timeout=project["http_timeout_s"])
        response.raise_for_status()
        size = int(response.headers.get("Content-Length", "0"))
        if size != int(entry["expected_bytes"]) or size <= 0 or size > max_single:
            raise ValueError(f"Pinned {region} archive size changed or exceeds limit: {size}")
        if response.url != entry["url"]:
            raise ValueError(f"Pinned {region} URL redirected unexpectedly: {response.url}")
        target = folder / Path(entry["url"]).name
        planned.append((region, entry, target, response, size))
    existing_raw = sum(path.stat().st_size for path in (ROOT / "data/raw").rglob("*") if path.is_file())
    new_bytes = sum(size for _, _, target, _, size in planned if not target.exists())
    if existing_raw + new_bytes > max_total:
        raise ValueError(f"OSM acquisition would exceed configured total raw-data limit: {existing_raw + new_bytes} > {max_total}")
    if shutil.disk_usage(ROOT).free < new_bytes * 3:
        raise ValueError("Insufficient free space for compressed and expanded OSM extracts")
    for region, entry, target, response, size in planned:
        source_record = {
            "region": region,
            "source_url": entry["url"],
            "archive_version": source["version"],
            "content_length": size,
            "last_modified": response.headers.get("Last-Modified", ""),
            "etag": response.headers.get("ETag", ""),
            "license": source["license"],
        }
        save_json(folder / f"{region}_source.json", source_record, source["id"], command=f"HEAD {entry['url']}")
        stream_file(client, entry["url"], target, source["id"], max_bytes=max_single, expected_kind="zip", timeout=project["http_timeout_s"])
        if target.stat().st_size != size:
            raise ValueError(f"Pinned {region} archive byte count changed after transfer")
        status_update(source["id"], "downloaded", f"{region} archive acquired; processing pending", last_region=region)
    return {"archives": len(planned), "bytes": sum(size for *_, size in planned), "folder": str(folder.relative_to(ROOT))}

import re
import sqlite3
import zipfile

import geopandas as gpd
import pandas as pd
import pyogrio
import yaml
from shapely.geometry import Point

from .metadata import register, relative, verify_manifest_entry

ADMIN_LAYER = "gis_osm_adminareas_a_free"
PLACE_LAYER = "gis_osm_places_free"


def _normal(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", " ", str(name).casefold()).strip()
    words = [word for word in value.split() if word not in {"kabupaten", "kota", "kotamadya", "kecamatan", "pulau", "daerah", "tingkat", "ii"}]
    return " ".join(words)


def polygon_eligible(claim: dict) -> bool:
    """Only explicit whole administrative units may use modern admin polygons."""
    return claim.get("scope") == "whole_admin" and claim.get("level") == 5 and claim.get("region") != "outside_indonesia"


def _extract_archive(archive: Path, destination: Path, source_id: str) -> Path:
    with zipfile.ZipFile(archive) as zipped:
        members = [member for member in zipped.infolist() if member.filename.endswith(".gpkg") and not member.is_dir()]
        if len(members) != 1 or members[0].file_size > 5 * 1024**3:
            raise ValueError(f"Expected exactly one bounded GeoPackage in {archive}")
        target = destination / Path(members[0].filename).name
        if target.exists():
            if target.stat().st_size != members[0].file_size:
                raise ValueError(f"Extracted GeoPackage size changed: {target}")
            verify_manifest_entry(target)
            return target
        destination.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".gpkg.part")
        with zipped.open(members[0]) as src, temp.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        temp.replace(target)
        if target.stat().st_size != members[0].file_size:
            raise ValueError(f"Extracted GeoPackage size mismatch: {target}")
        register(target, source_id, "GeoPackage", rows="OSM regional extract", parents=relative(archive), command="python -m indo_data process --all")
        return target


def _admin_matches(admin: gpd.GeoDataFrame, claim: dict) -> gpd.GeoDataFrame:
    level = f"admin_level{claim['level']}"
    keys = {_normal(claim["name"]), *(_normal(alias) for alias in claim.get("aliases", []))}
    matching = admin[(admin.fclass == level) & (admin.name.fillna("").map(_normal).isin(keys))].copy()
    province = claim.get("province")
    if province:
        parents = admin[(admin.fclass == "admin_level4") & (admin.name.fillna("").map(_normal) == _normal(province))]
        if len(parents) != 1:
            return matching.iloc[:0].copy()
        territory = parents.geometry.iloc[0]
        matching = matching[matching.geometry.representative_point().within(territory)]
    return matching


def _add_geometry(records: list[dict], claim: dict, feature: dict, geom, layer: str, region: str, *, rationale: str) -> None:
    records.append({"claim_id": claim["id"], "zone_id": claim["zone_id"], "legal_name": claim["name"], "legal_scope": claim["scope"], "instrument": claim["instrument"], "designation_date_text": claim.get("designation_date_text", ""), "date_precision": claim.get("date_precision", ""), "legal_locator": claim["locator"], "legal_url": claim["url"], "osm_id": str(feature.get("osm_id", "")), "osm_name": str(feature.get("name", "")), "osm_fclass": str(feature.get("fclass", "")), "region": region, "snapshot": "260924", "geometry_role": "current_location_proxy", "layer": layer, "match_rationale": rationale, "review_note": claim["note"], "geometry": geom})


def _empty_polygon_layer(path: Path) -> None:
    empty = gpd.GeoDataFrame({key: pd.Series(dtype="str") for key in ("claim_id", "zone_id", "osm_id", "geometry_role")}, geometry=gpd.GeoSeries([], crs="EPSG:4326"), crs="EPSG:4326")
    pyogrio.write_dataframe(empty, path, layer="kek_site_candidates", driver="GPKG", geometry_type="MultiPolygon", append=True)


def _site_name_eligible(name: str, zone: str) -> bool:
    allowed = {
        "Palu": {"kek palu", "kawasan ekonomi khusus palu", "palu special economic zone"},
        "Nongsa": {"kek nongsa", "kawasan ekonomi khusus nongsa", "nongsa digital park"},
    }
    return _normal(name) in allowed.get(zone, set())


def _kek_site_candidates(gpkg: Path, zone: str, reference: Point) -> list[dict]:
    """Require exact site name, nearby geometry, and a site-scale footprint."""
    found = []
    connection = sqlite3.connect(gpkg)
    try:
        for layer in ("gis_osm_landuse_a_free", "gis_osm_places_a_free", "gis_osm_pois_a_free", "gis_osm_buildings_a_free"):
            allowed = {"Palu": ("KEK Palu", "Kawasan Ekonomi Khusus Palu", "Palu Special Economic Zone"), "Nongsa": ("KEK Nongsa", "Kawasan Ekonomi Khusus Nongsa", "Nongsa Digital Park")}[zone]
            placeholders = ",".join("?" for _ in allowed)
            rows = connection.execute(f'SELECT fid, name FROM "{layer}" WHERE lower(name) IN ({placeholders})', tuple(name.lower() for name in allowed)).fetchall()
            fids = [fid for fid, name in rows if _site_name_eligible(name, zone)]
            if not fids:
                continue
            features = gpd.read_file(gpkg, layer=layer, where="fid IN (" + ",".join(map(str, fids)) + ")")
            for _, feature in features.iterrows():
                geom = feature.geometry
                if not geom.is_valid or geom.is_empty:
                    continue
                projected = gpd.GeoSeries([geom, reference], crs="EPSG:4326").to_crs(6933)
                if projected.iloc[0].area > 50_000_000 or projected.iloc[0].distance(projected.iloc[1]) > 10_000:
                    continue
                found.append({"osm_id": str(feature.osm_id), "name": str(feature["name"]), "fclass": str(feature.fclass), "geometry": geom})
    finally:
        connection.close()
    return found


def _select_kek_site(found: list[dict], zone: str) -> list[dict]:
    exact = [item for item in found if _normal(item["name"]) == f"kawasan ekonomi khusus {zone.casefold()}"]
    return exact if exact else found


def process_osm_policy(folder: Path, snapshot: str) -> dict:
    """Build current-place GIS; no legal treatment geometry is constructed."""
    claims = yaml.safe_load((ROOT / "config/policy_places.yaml").read_text())["places"]
    target_dir = ROOT / "data/processed/policy_treatment" / snapshot
    target_dir.mkdir(parents=True, exist_ok=True)
    interim = ROOT / "data/interim/geofabrik_osm_policy" / snapshot
    polygons: list[dict] = []
    points: list[dict] = []
    review: list[dict] = []
    extracts: dict[str, Path] = {}
    for region in ("sumatra", "kalimantan", "sulawesi", "papua", "maluku", "nusa_tenggara"):
        archives = list(folder.glob(f"{region.replace('_', '-')}-*-free.gpkg.zip"))
        if len(archives) != 1:
            raise ValueError(f"Missing or duplicate dated {region} Geofabrik archive")
        verify_manifest_entry(archives[0])
        extracts[region] = _extract_archive(archives[0], interim, "geofabrik_osm_policy")
    for region, gpkg in extracts.items():
        local = [claim for claim in claims if claim.get("region") == region]
        if not local:
            continue
        admin = gpd.read_file(gpkg, layer=ADMIN_LAYER)
        if admin.crs is None or admin.crs.to_authority() not in {("EPSG", "4326"), ("OGC", "CRS84")} or not admin.geometry.is_valid.all():
            raise ValueError(f"Invalid Geofabrik adminareas CRS or geometry: {region}")
        admin = admin.to_crs(4326)
        for claim in local:
            status = "unresolved"
            matches = gpd.GeoDataFrame()
            if claim.get("match_blocked_reason"):
                status = "historical_admin_identity_unresolved"
            elif claim["level"] in (5, 6):
                matches = _admin_matches(admin, claim)
            if len(matches) == 1:
                feature = matches.iloc[0]
                feature_data = {"osm_id": feature.osm_id, "name": feature["name"], "fclass": feature.fclass}
                if polygon_eligible(claim):
                    rationale = "Unique legal name or recorded spelling alias, OSM admin level, regional extract and province polygon; decree names entire unit"
                    _add_geometry(polygons, claim, feature_data, feature.geometry, "kapet_whole_unit_proxies", region, rationale=rationale)
                    status = "modern_polygon_proxy"
                else:
                    _add_geometry(points, claim, feature_data, feature.geometry.representative_point(), "kapet_review_points", region, rationale="Unique modern admin feature anchors named partial area; point does not describe designated extent")
                    status = "review_point_partial_area"
            elif claim["level"] == 0:
                # Island names are searched in the dated OSM places layer. A point is only a cue for review.
                escaped = claim["name"].replace("'", "''")
                places = gpd.read_file(gpkg, layer=PLACE_LAYER, where=f"name = '{escaped}' OR name = 'Pulau {escaped}'")
                if len(places) == 1:
                    feature = places.iloc[0]
                    _add_geometry(points, claim, {"osm_id": feature.osm_id, "name": feature["name"], "fclass": feature.fclass}, feature.geometry, "kapet_review_points", region, rationale="Unique exact OSM island place name; island shoreline and annex remain unverified")
                    status = "review_point_island"
                else:
                    status = "unresolved_island_name"
            elif claim.get("match_blocked_reason"):
                status = "historical_admin_identity_unresolved"
            elif len(matches) > 1:
                status = "ambiguous_osm_name"
            else:
                status = "no_unique_osm_match"
            review.append({"claim_id": claim["id"], "zone_id": claim["zone_id"], "name": claim["name"], "scope": claim["scope"], "region": region, "osm_match_count": len(matches) if claim["level"] else "", "status": status, "legal_url": claim["url"], "legal_locator": claim["locator"], "review_note": claim["note"]})
    for claim in claims:
        if claim.get("region") == "outside_indonesia":
            review.append({"claim_id": claim["id"], "zone_id": claim["zone_id"], "name": claim["name"], "scope": claim["scope"], "region": "outside_indonesia", "osm_match_count": 0, "status": "outside_current_indonesia_extracts", "legal_url": claim["url"], "legal_locator": claim["locator"], "review_note": claim["note"]})
    if not polygons or not points:
        raise ValueError("OSM policy GIS lacks expected KAPET polygon or review point layers")
    target = target_dir / "policy_location_proxies.gpkg"
    if target.exists():
        target.unlink()
    for layer, data in (("kapet_whole_unit_proxies", polygons), ("kapet_review_points", points)):
        frame = gpd.GeoDataFrame(data, geometry="geometry", crs="EPSG:4326")
        frame.to_file(target, driver="GPKG", layer=layer, mode="a")
    kek_path = target_dir / "kek_registry.csv"
    if not kek_path.exists():
        raise ValueError("Official KEK registry must be processed before OSM policy GIS")
    kek = pd.read_csv(kek_path)
    kek_points = []
    kek_polygons = []
    for _, item in kek.iterrows():
        if pd.isna(item.current_reference_longitude) or pd.isna(item.current_reference_latitude):
            continue
        kek_points.append({"claim_id": "kek_" + str(item.slug), "zone_id": str(item.zone_id), "legal_name": str(item.name_original), "legal_scope": "official_reference_point", "instrument": str(item.designation_instrument_text), "legal_locator": "Official KEK detail page, coordinates", "legal_url": str(item.source_url), "osm_id": "", "osm_name": "", "osm_fclass": "", "region": "", "snapshot": snapshot, "geometry_role": "current_location_proxy", "layer": "kek_official_reference_points", "match_rationale": "Coordinate published on official KEK site; exact site polygon not established", "review_note": "Reference point only; no official site boundary", "geometry": Point(float(item.current_reference_longitude), float(item.current_reference_latitude))})
        region = "sulawesi" if item.name_original == "Palu" else "sumatra" if item.name_original == "Nongsa" else ""
        if region:
            found = _select_kek_site(_kek_site_candidates(extracts[region], str(item.name_original), kek_points[-1]["geometry"]), str(item.name_original))
            if len(found) == 1:
                claim = {"id": "kek_" + str(item.slug), "zone_id": str(item.zone_id), "name": str(item.name_original), "scope": "specific_site_candidate", "instrument": str(item.designation_instrument_text), "locator": "Official KEK detail page, coordinates", "url": str(item.source_url), "note": "OSM named site polygon; official boundary remains unverified"}
                _add_geometry(kek_polygons, claim, found[0], found[0]["geometry"], "kek_site_candidates", region, rationale="Exact site-specific OSM name, within 10 km of official KEK coordinate, footprint at most 50 km2; candidate only")
                review.append({"claim_id": claim["id"], "zone_id": claim["zone_id"], "name": claim["name"], "scope": claim["scope"], "region": region, "osm_match_count": 1, "status": "osm_site_polygon_candidate", "legal_url": claim["url"], "legal_locator": claim["locator"], "review_note": "Exact OSM named site; official boundary still unverified"})
            elif len(found) > 1:
                review.append({"claim_id": "kek_" + str(item.slug), "zone_id": str(item.zone_id), "name": str(item.name_original), "scope": "specific_site_candidate", "region": region, "osm_match_count": len(found), "status": "ambiguous_site_polygons", "legal_url": str(item.source_url), "legal_locator": "Official KEK detail page", "review_note": "Multiple exact site names; site boundary unresolved"})
            else:
                review.append({"claim_id": "kek_" + str(item.slug), "zone_id": str(item.zone_id), "name": str(item.name_original), "scope": "specific_site_candidate", "region": region, "osm_match_count": 0, "status": "no_exact_site_polygon", "legal_url": str(item.source_url), "legal_locator": "Official KEK detail page", "review_note": "Official reference point available; no site polygon accepted"})
    if kek_polygons:
        gpd.GeoDataFrame(kek_polygons, geometry="geometry", crs="EPSG:4326").to_file(target, driver="GPKG", layer="kek_site_candidates", mode="a")
    else:
        _empty_polygon_layer(target)
    gpd.GeoDataFrame(kek_points, geometry="geometry", crs="EPSG:4326").to_file(target, driver="GPKG", layer="kek_official_reference_points", mode="a")
    all_geometries = polygons + points + kek_polygons + kek_points
    crosswalk = pd.DataFrame([{key: value for key, value in row.items() if key != "geometry"} for row in all_geometries])
    crosswalk.insert(0, "proxy_id", [f"proxy_{i:03d}" for i in range(1, len(crosswalk) + 1)])
    crosswalk_path = target_dir / "policy_location_crosswalk.csv"
    crosswalk.to_csv(crosswalk_path, index=False)
    review_path = target_dir / "policy_location_review.csv"
    by_id = {claim["id"]: claim for claim in claims}
    for row in review:
        claim = by_id.get(row["claim_id"], {})
        row["designation_date_text"] = claim.get("designation_date_text", "")
        row["date_precision"] = claim.get("date_precision", "")
    pd.DataFrame(review).to_csv(review_path, index=False)
    parents = ";".join(relative(path) for path in extracts.values())
    register(target, "geofabrik_osm_policy", "GeoPackage", rows=str(len(all_geometries)), parents=parents, command="python -m indo_data process --all")
    register(crosswalk_path, "geofabrik_osm_policy", "CSV", rows=str(len(crosswalk)), parents=relative(target), command="python -m indo_data process --all")
    register(review_path, "official_kapet_decrees", "CSV", rows=str(len(review)), parents="config/policy_places.yaml", command="python -m indo_data process --all")
    status_update("geofabrik_osm_policy", "verified", "Six dated OSM extracts matched to legal place claims; modern proxy GIS and unresolved queue produced", polygons=len(polygons), review_points=len(points), kek_reference_points=len(kek_points), unresolved=sum("unresolved" in r["status"] or "no_unique" in r["status"] or "ambiguous" in r["status"] or "outside" in r["status"] for r in review))
    return {"polygons": len(polygons), "review_points": len(points), "kek_reference_points": len(kek_points), "review_rows": len(review)}
