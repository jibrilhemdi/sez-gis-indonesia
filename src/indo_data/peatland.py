from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from .coast_bathymetry import inspect_raster
from .metadata import ROOT, register, status_update


def inspect_peat_raster(path: Path) -> dict:
    """Import check only; publisher legend is required before a binary mask."""
    result = inspect_raster(path)
    result["mask_status"] = "not_created_pending_legend_review"
    return result


def process_government_peat(path: Path, snapshot: str) -> dict:
    polygons = gpd.read_file(path)
    if polygons.empty or polygons.crs is None or not polygons.geometry.is_valid.all():
        raise ValueError("Government peat layer has invalid polygons or CRS")
    if not polygons.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        raise ValueError("Government peat layer includes nonpolygon geometry")
    output = ROOT / "data/processed/peatland" / snapshot
    output.mkdir(parents=True, exist_ok=True)
    target = output / "big_peta_lahan_gambut_partial.gpkg"
    polygons.to_file(target, driver="GPKG", layer="big_peta_lahan_gambut")
    result = {"features": len(polygons), "bounds": tuple(polygons.total_bounds), "crs": str(polygons.crs), "usda1_values": sorted(str(v) for v in polygons.usda1.dropna().unique()) if "usda1" in polygons else []}
    register(target, "big_peta_lahan_gambut", "GeoPackage", extent=str(result["bounds"]), rows=str(len(polygons)), parents=str(path.relative_to(ROOT)), command="python -m indo_data process --all")
    status_update("big_peta_lahan_gambut", "partial", "Verified supplementary government peat polygons; only regional coverage, not CIFOR substitute", **result)
    return result
