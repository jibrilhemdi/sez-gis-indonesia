from __future__ import annotations

import calendar
import csv
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import yaml

from .metadata import ROOT, sha256


def run_validation(snapshot: str) -> tuple[list[str], list[str]]:
    checks = []
    failures = []
    manifest = ROOT / "metadata/file_manifest.csv"
    if not manifest.exists():
        return checks, ["No file manifest"]
    with manifest.open(newline="") as handle:
        entries = list(csv.DictReader(handle))
    for item in entries:
        path = ROOT / item["path"]
        if not path.exists() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            failures.append(f"Manifest mismatch: {item['path']}")
    checks.append(f"Manifest: {len(entries)} paths checked for bytes and SHA-256; {len(failures)} mismatch(es).")

    adm0_path = ROOT / "data/processed/boundary" / snapshot / "indonesia_adm0.gpkg"
    if adm0_path.exists():
        adm0 = gpd.read_file(adm0_path)
        if len(adm0) != 1 or adm0.crs.to_epsg() != 4326 or not adm0.geometry.is_valid.all():
            failures.append("ADM0 feature count, CRS, or geometry invalid")
        islands = sum(len(geom.geoms) if geom.geom_type == "MultiPolygon" else 1 for geom in adm0.geometry)
        checks.append(f"Indonesia ADM0: {len(adm0)} valid national feature, {islands:,} polygon components; small-island completeness unverified against independent coast data.")
    else:
        checks.append("SKIPPED ADM0 QA: file absent.")

    daily_path = ROOT / "data/processed/port_activity" / snapshot / "daily.parquet"
    points_path = ROOT / "data/processed/port_activity" / snapshot / "portwatch_ports.gpkg"
    if daily_path.exists() and points_path.exists():
        daily = pd.read_parquet(daily_path)
        points = gpd.read_file(points_path)
        if daily.duplicated(["port_id", "date"]).any() or daily.source_object_id.duplicated().any():
            failures.append("PortWatch daily duplicate port/date or source object ID")
        if not daily.country_iso3.eq("IDN").all():
            failures.append("PortWatch daily includes non-IDN records")
        point_ids = set(points.portid)
        daily_ids = set(daily.port_id)
        missing_geometry = daily_ids - point_ids
        missing_activity = point_ids - daily_ids
        if points.geometry.isna().any() or not points.geometry.is_valid.all() or not points.geometry.x.between(90, 145).all() or not points.geometry.y.between(-15, 10).all():
            failures.append("PortWatch point geometry or coordinate order invalid")
        checks.append(f"PortWatch: {len(daily):,} daily rows, {len(daily_ids)} activity ports, {len(points)} current points; {len(missing_geometry)} activity IDs without geometry, {len(missing_activity)} points without activity; actual dates {daily.date.min()} to {daily.date.max()}.")
        for frequency in ("month", "year"):
            frame = pd.read_parquet(daily_path.parent / f"{frequency}ly.parquet")
            if frame.duplicated(["port_id", "period"]).any():
                failures.append(f"Duplicate PortWatch {frequency} grain")
            periods = pd.PeriodIndex(frame.period, freq="M" if frequency == "month" else "Y")
            expected = np.array([(p.end_time.date() - p.start_time.date()).days + 1 for p in periods])
            if not np.array_equal(frame.expected_calendar_days.to_numpy(), expected):
                failures.append(f"Incorrect PortWatch {frequency} calendar-day counts")
            if not np.allclose(frame.coverage_ratio.to_numpy(), frame.observed_days.to_numpy() / expected):
                failures.append(f"Incorrect PortWatch {frequency} coverage ratios")
            if not np.array_equal(frame.partial_period.to_numpy(), frame.observed_days.to_numpy() < expected):
                failures.append(f"Incorrect PortWatch {frequency} partial flags")
            checks.append(f"PortWatch {frequency}: {len(frame):,} rows; grain, expected days, coverage ratios, and partial flags checked.")
    else:
        checks.append("SKIPPED PortWatch table/point QA: required files absent.")

    big_path = ROOT / "data/processed/ports_historical" / snapshot / "ports_current.gpkg"
    if big_path.exists():
        big = gpd.read_file(big_path)
        if big.duplicated(["source_layer_id", "objectid"]).any() or not big.geometry.is_valid.all():
            failures.append("BIG current ports duplicate IDs or invalid geometry")
        if not big.geometry.x.between(90, 145).all() or not big.geometry.y.between(-15, 10).all():
            failures.append("BIG current ports coordinate order/bounds invalid")
        checks.append(f"BIG current inventory: {len(big):,} rows, valid points, unique layer/object IDs. Historical year fields audited separately.")
    else:
        checks.append("SKIPPED BIG current inventory QA: file absent.")

    historical_path = ROOT / "data/processed/ports_historical" / snapshot / "port_presence_1992_2020.parquet"
    if historical_path.exists():
        presence = pd.read_parquet(historical_path)
        if presence.duplicated(["port_id", "year"]).any() or not set(presence.presence_status).issubset({"documented_present", "documented_absent", "inferred_present", "unknown"}):
            failures.append("Historical presence key or state invalid")
        if presence.loc[presence.year > 1995, "presence_status"].ne("unknown").any():
            failures.append("Unsupported post-1995 IAPH presence inferred")
        checks.append(f"Historical evidence: {presence.port_id.nunique()} ports, {len(presence):,} port-years; post-1995 states unknown and geometry unassigned.")
    else:
        checks.append("SKIPPED historical presence QA: evidence file absent.")

    peat_path = ROOT / "data/processed/peatland" / snapshot / "big_peta_lahan_gambut_partial.gpkg"
    if peat_path.exists():
        peat = gpd.read_file(peat_path)
        if peat.empty or not peat.geometry.is_valid.all():
            failures.append("BIG supplementary peat geometry invalid")
        checks.append(f"BIG supplementary peat: {len(peat)} valid regional polygons, bounds {tuple(round(float(v), 3) for v in peat.total_bounds)}; no national non-peat inference.")
    else:
        checks.append("SKIPPED peat polygon QA: file absent.")

    coast_path = ROOT / "data/processed/coast_bathymetry" / snapshot / "regional_coastline.gpkg"
    if coast_path.exists():
        coast = gpd.read_file(coast_path)
        if coast.empty or not coast.geometry.is_valid.all():
            failures.append("Coastline empty or invalid")
        checks.append(f"OSM coastline: {len(coast):,} valid regional lines; country attribution unresolved.")
    else:
        checks.append("SKIPPED coastline QA: file absent.")

    rasters = {}
    for kind in ("elevation", "tid"):
        path = ROOT / "data/processed/coast_bathymetry" / snapshot / f"gebco_2026_{kind}_regional.tif"
        if path.exists():
            with rasterio.open(path) as source:
                rasters[kind] = (source.shape, tuple(source.bounds), source.crs.to_epsg(), source.dtypes[0])
                if source.width <= 0 or source.height <= 0 or source.crs.to_epsg() != 4326:
                    failures.append(f"GEBCO {kind} dimensions/CRS invalid")
                values = source.read(1, masked=True)
                minimum, maximum = float(values.min()), float(values.max())
                checks.append(f"GEBCO {kind}: {source.height} × {source.width}, EPSG:{source.crs.to_epsg()}, {source.dtypes[0]}, min={minimum:g}, max={maximum:g}, nodata={source.nodata}.")
                if kind == "elevation" and not (minimum < 0 < maximum):
                    failures.append("GEBCO signed elevation convention not observed")
        else:
            checks.append(f"SKIPPED GEBCO {kind} QA: file absent.")
    if len(rasters) == 2 and rasters["elevation"][:3] != rasters["tid"][:3]:
        failures.append("GEBCO elevation/TID shape, extent or CRS mismatch")

    kapet_path = ROOT / "data/processed/policy_treatment" / snapshot / "kapet_registry.csv"
    if kapet_path.exists():
        kapet = pd.read_csv(kapet_path)
        if kapet.zone_id.duplicated().any() or kapet.treated_status.ne("unknown").any() or kapet.geometry_status.ne("unknown").any():
            failures.append("KAPET partial registry IDs or unknown status invalid")
        checks.append(f"KAPET: {len(kapet)} documented designation candidates; no treatment polygons or national non-treatment labels.")
    else:
        checks.append("SKIPPED KAPET registry QA: file absent.")

    kek_path = ROOT / "data/processed/policy_treatment" / snapshot / "kek_registry.csv"
    if kek_path.exists():
        kek = pd.read_csv(kek_path)
        if kek.zone_id.duplicated().any() or kek.geometry_status.ne("unverified").any() or kek.designation_date.notna().any():
            failures.append("KEK partial registry IDs, geometry, or unverified dates invalid")
        checks.append(f"KEK: {len(kek)} unique official detail records; legal dates blank and geometry unverified; national completeness not asserted.")
    else:
        checks.append("SKIPPED KEK registry QA: file absent.")

    proxy_path = ROOT / "data/processed/policy_treatment" / snapshot / "policy_location_proxies.gpkg"
    if proxy_path.exists():
        from .osm_policy import _normal, _site_name_eligible, polygon_eligible
        layer_names = {item for item in gpd.list_layers(proxy_path).name}
        required_layers = {"kapet_whole_unit_proxies", "kapet_review_points", "kek_site_candidates", "kek_official_reference_points"}
        if not required_layers.issubset(layer_names):
            failures.append("Policy proxy GeoPackage missing required layers")
        claims = {item["id"]: item for item in yaml.safe_load((ROOT / "config/policy_places.yaml").read_text())["places"]}
        registry = set(pd.read_csv(kapet_path).zone_id) if kapet_path.exists() else set()
        crosswalk = pd.read_csv(proxy_path.parent / "policy_location_crosswalk.csv", dtype={"osm_id": "string", "zone_id": "string"}).fillna("")
        review = pd.read_csv(proxy_path.parent / "policy_location_review.csv").fillna("")
        if crosswalk.proxy_id.duplicated().any() or crosswalk.duplicated(["layer", "claim_id", "osm_id"]).any():
            failures.append("Policy proxy crosswalk has duplicate identifiers")
        osm_rows = crosswalk[crosswalk.osm_id.ne("")]
        if osm_rows.osm_id.duplicated().any() or osm_rows.snapshot.ne("260924").any():
            failures.append("OSM source IDs or dated snapshot invalid")
        for _, row in crosswalk[crosswalk.layer.str.startswith("kapet_")].iterrows():
            claim = claims.get(row.claim_id)
            allowed = {_normal(claim["name"]), *(_normal(alias) for alias in claim.get("aliases", []))} if claim else set()
            if claim is None or _normal(row.osm_name) not in allowed or row.legal_url != claim["url"] or row.legal_locator != claim["locator"]:
                failures.append(f"Legal-to-OSM name or citation mismatch: {row.claim_id}")
        if set(claims) - set(review.claim_id):
            failures.append("Policy legal place claims absent from review queue")
        if set(review.zone_id) - registry - set(pd.read_csv(kek_path).zone_id):
            failures.append("Policy review references unknown zone")
        total_features = 0
        for layer in required_layers & layer_names:
            frame = gpd.read_file(proxy_path, layer=layer)
            total_features += len(frame)
            if frame.crs is None or frame.crs.to_epsg() != 4326 or (len(frame) and (frame.geometry.isna().any() or not frame.geometry.is_valid.all())):
                failures.append(f"Policy proxy invalid CRS or geometry: {layer}")
            if len(frame) and (frame.geometry_role.ne("current_location_proxy").any() or frame.duplicated(["claim_id", "osm_id"]).any()):
                failures.append(f"Policy proxy invalid role or duplicate source feature: {layer}")
            if layer == "kapet_whole_unit_proxies":
                if not frame.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all() or any(not polygon_eligible(claims[item]) for item in frame.claim_id):
                    failures.append("Partial or island wording yielded a whole-unit polygon")
                if set(frame.zone_id) - registry:
                    failures.append("KAPET polygon references unknown designation")
            elif layer == "kapet_review_points" and not frame.geometry.geom_type.eq("Point").all():
                failures.append("KAPET review layer must contain points")
            elif layer == "kek_site_candidates":
                if len(frame) and (not frame.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all() or any(not _site_name_eligible(row.osm_name, row.legal_name) for _, row in frame.iterrows())):
                    failures.append("KEK site candidate is not an exact named site polygon")
            elif layer == "kek_official_reference_points" and not frame.geometry.geom_type.eq("Point").all():
                failures.append("KEK official reference layer must contain points")
            if len(frame):
                pairs = set(zip(frame.claim_id, frame.osm_id))
                corresponding = crosswalk[crosswalk.layer.eq(layer)]
                if pairs != set(zip(corresponding.claim_id, corresponding.osm_id)):
                    failures.append(f"Policy crosswalk mismatch: {layer}")
        if total_features != len(crosswalk):
            failures.append("Policy proxy feature count differs from crosswalk")
        checks.append(f"Policy location GIS: {total_features} valid modern proxy features in four layers; {len(review)} legal/site review rows, including unresolved claims; no historical treatment labels.")
    else:
        checks.append("SKIPPED policy location GIS QA: file absent.")

    evidence_path = ROOT / "metadata/evidence.csv"
    if evidence_path.exists():
        evidence = pd.read_csv(evidence_path)
        required = ["evidence_id", "entity_id", "claim_field", "source_id", "url", "page_article_table", "review_status"]
        if evidence.evidence_id.duplicated().any() or evidence[required].isna().any().any():
            failures.append("Manual evidence IDs or required provenance fields invalid")
        checks.append(f"Manual evidence: {len(evidence)} distinct claims with source, locator, and review status.")
    else:
        checks.append("SKIPPED manual evidence QA: file absent.")

    checks.append("SKIPPED peat raster mask/class QA: CIFOR raster and verified legend were not acquired; no binary mask was created.")
    checks.append("SKIPPED historical port crosswalk ambiguity QA: no automated cross-source match was accepted; all candidates remain in review queues.")
    checks.append("SKIPPED KAPET/KEK polygon overlap QA: no legally verified treatment boundaries were acquired.")

    return checks, failures
