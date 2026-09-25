from __future__ import annotations

import calendar
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from .metadata import ROOT, register, status_update


def read_batches(folder: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(folder.glob("batch_*.json")):
        value = json.loads(path.read_text())
        for feature in value["features"]:
            row = dict(feature["attributes"])
            if feature.get("geometry"):
                row["_geometry"] = feature["geometry"]
            rows.append(row)
    return rows


def aggregate_activity(daily: pd.DataFrame, frequency: str, measures: list[str]) -> pd.DataFrame:
    if frequency not in ("month", "year"):
        raise ValueError(frequency)
    frame = daily.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["period"] = frame["date"].dt.to_period("M" if frequency == "month" else "Y")
    result: list[dict] = []
    for (port_id, period), block in frame.groupby(["port_id", "period"], dropna=False, sort=True):
        start = period.start_time.date()
        end = period.end_time.date()
        expected = (end - start).days + 1
        observed = block["date"].dt.normalize().nunique()
        row = {"port_id": port_id, "period": str(period), "period_start": str(start), "period_end": str(end), "observed_days": int(observed), "expected_calendar_days": expected, "coverage_ratio": observed / expected, "partial_period": observed < expected}
        for col in measures:
            count = block[col].notna().sum()
            row[col] = block[col].sum(min_count=1)
            row[f"{col}_missing_days"] = int(expected - count)
        result.append(row)
    return pd.DataFrame(result)


def process_daily(folder: Path, snapshot: str) -> dict:
    rows = read_batches(folder)
    if not rows:
        raise ValueError("No daily activity rows")
    frame = pd.DataFrame(rows)
    required = {"ObjectId", "date", "portid", "ISO3"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing required daily fields: {required - set(frame.columns)}")
    if not frame["ISO3"].eq("IDN").all():
        raise ValueError("Non-Indonesian daily records in extract")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.strftime("%Y-%m-%d")
    if frame["ObjectId"].duplicated().any() or frame.duplicated(["portid", "date"]).any():
        raise ValueError("Duplicate daily object ID or port/date")
    frame = frame.rename(columns={"portid": "port_id", "portname": "port_name_original", "ObjectId": "source_object_id", "ISO3": "country_iso3"})
    measures = [col for col in frame.columns if col.startswith(("portcalls_", "import_", "export_")) or col in ("portcalls", "import", "export")]
    for col in measures:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    output = ROOT / "data/processed/port_activity" / snapshot
    output.mkdir(parents=True, exist_ok=True)
    daily_path = output / "daily.parquet"
    frame.to_parquet(daily_path, index=False)
    register(daily_path, "imf_portwatch_daily", "Parquet", rows=str(len(frame)), temporal=f"{frame.date.min()}/{frame.date.max()}", parents=str(folder.relative_to(ROOT)), command="python -m indo_data process --all")
    for frequency in ("month", "year"):
        agg = aggregate_activity(frame, frequency, measures)
        target = output / f"{frequency}ly.parquet"
        agg.to_parquet(target, index=False)
        register(target, "imf_portwatch_daily", "Parquet", rows=str(len(agg)), temporal=f"{agg.period.min()}/{agg.period.max()}", parents=str(daily_path.relative_to(ROOT)), command="python -m indo_data process --all")
    coverage = frame.groupby("port_id", dropna=False).agg(first_observed_date=("date", "min"), last_observed_date=("date", "max"), observed_rows=("date", "size")).reset_index()
    coverage_path = output / "port_coverage.csv"
    coverage.to_csv(coverage_path, index=False)
    register(coverage_path, "imf_portwatch_daily", "CSV", rows=str(len(coverage)), parents=str(daily_path.relative_to(ROOT)))
    status_update("imf_portwatch_daily", "verified", "Daily, monthly, annual tables processed", rows=len(frame), first_observed_date=frame.date.min(), last_observed_date=frame.date.max(), ports=int(frame.port_id.nunique()))
    return {"rows": len(frame), "ports": frame.port_id.nunique(), "first": frame.date.min(), "last": frame.date.max()}


def process_points(folder: Path, snapshot: str) -> dict:
    rows = read_batches(folder)
    if not rows:
        raise ValueError("No PortWatch points")
    frame = pd.DataFrame(rows)
    if "_geometry" not in frame:
        raise ValueError("PortWatch points have no geometry")
    geometry = frame.pop("_geometry").map(lambda item: Point(item["x"], item["y"]) if isinstance(item, dict) and "x" in item and "y" in item else None)
    points = gpd.GeoDataFrame(frame, geometry=geometry, crs="EPSG:4326")
    if points.geometry.isna().any() or not points.geometry.is_valid.all() or not all(points.geometry.x.between(90, 145) & points.geometry.y.between(-15, 10)):
        raise ValueError("Invalid Indonesia PortWatch coordinates")
    output = ROOT / "data/processed/port_activity" / snapshot
    output.mkdir(parents=True, exist_ok=True)
    target = output / "portwatch_ports.gpkg"
    points.to_file(target, driver="GPKG", layer="portwatch_ports")
    register(target, "imf_portwatch_ports", "GeoPackage", extent=str(tuple(points.total_bounds)), rows=str(len(points)), parents=str(folder.relative_to(ROOT)), command="python -m indo_data process --all")
    status_update("imf_portwatch_ports", "verified", f"ArcGIS IDs reconciled; {len(points)} current points reopened as valid geometry", rows=len(points))
    return {"rows": len(points), "columns": list(points.columns)}
