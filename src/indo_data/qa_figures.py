from __future__ import annotations

from pathlib import Path
import os

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[2] / ".mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(__file__).resolve().parents[2] / ".cache"))

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import rasterio
from shapely.geometry import box

from .metadata import ROOT


def create_figures(snapshot: str) -> list[str]:
    output = ROOT / "reports/figures"
    output.mkdir(parents=True, exist_ok=True)
    made = []
    boundary_path = ROOT / "data/processed/boundary" / snapshot / "indonesia_adm0.gpkg"
    if not boundary_path.exists():
        return made
    boundary = gpd.read_file(boundary_path)
    points_path = ROOT / "data/processed/port_activity" / snapshot / "portwatch_ports.gpkg"
    if points_path.exists():
        points = gpd.read_file(points_path)
        fig, ax = plt.subplots(figsize=(12, 5))
        boundary.boundary.plot(ax=ax, color="0.45", linewidth=0.4)
        points.plot(ax=ax, color="#126e82", markersize=9)
        ax.set(xlim=(93, 143), ylim=(-13, 8), title=f"PortWatch current Indonesia reference points (n={len(points)})", xlabel="Longitude", ylabel="Latitude")
        ax.text(0.01, 0.02, "Current points; historical locations unverified", transform=ax.transAxes, fontsize=8)
        fig.tight_layout()
        path = output / "portwatch_current_points.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        made.append(str(path.relative_to(ROOT)))
    peat_path = ROOT / "data/processed/peatland" / snapshot / "big_peta_lahan_gambut_partial.gpkg"
    if peat_path.exists():
        peat = gpd.read_file(peat_path)
        fig, ax = plt.subplots(figsize=(12, 5))
        boundary.plot(ax=ax, facecolor="#eeeeee", edgecolor="0.5", linewidth=0.4)
        peat.plot(ax=ax, color="#6f3f80", linewidth=0)
        ax.set(xlim=(93, 143), ylim=(-13, 8), title=f"BIG government peat-soil polygons (n={len(peat)}), partial coverage", xlabel="Longitude", ylabel="Latitude")
        ax.text(0.01, 0.02, "Grey land = peat coverage unknown, not non-peat", transform=ax.transAxes, fontsize=8)
        fig.tight_layout()
        path = output / "government_peat_partial_coverage.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        made.append(str(path.relative_to(ROOT)))
    coast_path = ROOT / "data/processed/coast_bathymetry" / snapshot / "regional_coastline.gpkg"
    elevation_path = ROOT / "data/processed/coast_bathymetry" / snapshot / "gebco_2026_elevation_regional.tif"
    if coast_path.exists():
        coast = gpd.read_file(coast_path)
        fig, ax = plt.subplots(figsize=(12, 5))
        coast.plot(ax=ax, color="#3f6686", linewidth=0.18)
        boundary.boundary.plot(ax=ax, color="black", linewidth=0.35)
        if elevation_path.exists():
            with rasterio.open(elevation_path) as source:
                extent = box(*source.bounds)
            gpd.GeoSeries([extent], crs="EPSG:4326").boundary.plot(ax=ax, color="#d46a33", linewidth=1)
        ax.set(xlim=(93, 143), ylim=(-13, 8), title="Acquired regional OSM coastline and GEBCO extent", xlabel="Longitude", ylabel="Latitude")
        ax.text(0.01, 0.02, "Blue includes neighbouring coasts; orange is GEBCO extent", transform=ax.transAxes, fontsize=8)
        fig.tight_layout()
        path = output / "coast_gebco_extent.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        made.append(str(path.relative_to(ROOT)))
    proxy_path = ROOT / "data/processed/policy_treatment" / snapshot / "policy_location_proxies.gpkg"
    if proxy_path.exists():
        whole = gpd.read_file(proxy_path, layer="kapet_whole_unit_proxies")
        review = gpd.read_file(proxy_path, layer="kapet_review_points")
        sites = gpd.read_file(proxy_path, layer="kek_site_candidates")
        kek = gpd.read_file(proxy_path, layer="kek_official_reference_points")
        fig, ax = plt.subplots(figsize=(13, 6))
        boundary.plot(ax=ax, facecolor="#f2f2f2", edgecolor="#999999", linewidth=0.25)
        whole.plot(ax=ax, facecolor="#8abbd2", edgecolor="#17627a", linewidth=0.65, alpha=0.75, label="KAPET whole-unit modern proxies")
        review.plot(ax=ax, color="#d77616", markersize=14, marker="o", label="KAPET review points")
        if len(sites):
            sites.plot(ax=ax, facecolor="none", edgecolor="#7e3f9c", linewidth=1.5, label="KEK exact named OSM site candidates")
        kek.plot(ax=ax, color="#7e3f9c", markersize=35, marker="D", label="KEK official reference points")
        ax.set(xlim=(93, 143), ylim=(-13, 8), title="Policy locations: dated modern proxies and review points", xlabel="Longitude", ylabel="Latitude")
        ax.legend(loc="lower left", fontsize=8)
        ax.text(0.01, 0.98, "Modern location proxies only; historical treatment status remains unknown", transform=ax.transAxes, fontsize=8, va="top", bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"})
        fig.tight_layout()
        path = output / "policy_location_proxies.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        made.append(str(path.relative_to(ROOT)))
    return made
