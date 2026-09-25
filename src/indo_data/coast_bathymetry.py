from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import rasterio

from .metadata import ROOT, register, status_update


def process_coast(archive: Path, bbox: list[float], snapshot: str) -> dict:
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        shapefiles = [name for name in names if name.lower().endswith(".shp")]
        if len(shapefiles) != 1:
            raise ValueError(f"Expected one coastline shapefile; got {shapefiles}")
    path = f"/vsizip/{archive.resolve()}/{shapefiles[0]}"
    lines = gpd.read_file(path, bbox=tuple(bbox))
    if lines.empty or lines.crs is None or lines.crs.to_epsg() != 4326:
        raise ValueError("Coastline has no features or unexpected CRS")
    lines = lines[lines.geometry.notna() & ~lines.geometry.is_empty].copy()
    if not lines.geometry.is_valid.all():
        raise ValueError("Invalid coastline line geometries")
    lines["context_role"] = "regional_coast_unclassified"
    lines["snapshot_date"] = snapshot
    output = ROOT / "data/processed/coast_bathymetry" / snapshot
    output.mkdir(parents=True, exist_ok=True)
    target = output / "regional_coastline.gpkg"
    lines.to_file(target, layer="regional_coastline", driver="GPKG")
    register(target, "osmdata_coastlines", "GeoPackage", extent=str(tuple(lines.total_bounds)), rows=str(len(lines)), parents=str(archive.relative_to(ROOT)), command="python -m indo_data process --all")
    result = {"features": len(lines), "bbox": tuple(lines.total_bounds), "crs": str(lines.crs), "classification": "regional coast; Indonesia/context attribution unresolved"}
    (output / "extent_report.json").write_text(json.dumps(result, indent=2) + "\n")
    register(output / "extent_report.json", "osmdata_coastlines", "JSON", parents=str(target.relative_to(ROOT)))
    status_update("osmdata_coastlines", "partial", "Regional processed coastline verified; country segment attribution unresolved", **result)
    return result


def inspect_raster(path: Path) -> dict:
    with rasterio.open(path) as source:
        if source.count < 1 or source.width <= 0 or source.height <= 0 or source.crs is None:
            raise ValueError("Raster has invalid dimensions or CRS")
        return {"width": source.width, "height": source.height, "bands": source.count, "crs": str(source.crs), "bounds": tuple(source.bounds), "nodata": source.nodata, "dtype": source.dtypes[0], "resolution": source.res}
