# QGIS guide: Indonesia bathymetry and policy location proxies

## GEBCO bathymetry

The Indonesia GEBCO_2026 download is complete. In QGIS, use **Layer → Add Layer → Add Raster Layer** and open:

- `data/processed/coast_bathymetry/2026-09-25/gebco_2026_elevation_regional.tif`
- `data/processed/coast_bathymetry/2026-09-25/gebco_2026_tid_regional.tif`

Both are EPSG:4326, 15 arc-second cells, and cover 93–143°E, 13°S–8°N. Place the elevation raster below vector layers. In **Layer Properties → Symbology**, choose *Singleband pseudocolor*, set a diverging ramp with the break at **0 metres**, and use blue tones for negative depth and land tones for positive elevation. Negative values are seabed height below mean sea level; positive values are land elevation. Do not take the absolute value of the raster. For a sea-only bathymetry display, use a raster calculator expression such as `"gebco_2026_elevation_regional@1" < 0` as a mask, while keeping the original intact.

The TID raster is a **categorical Type Identifier**, not a second elevation measurement. Style it with **Paletted/Unique values**; do not use a continuous elevation ramp or interpolate its values. Consult the GEBCO_2026 TID legend for category interpretation and survey/source limitations. Zoom to either raster to see the Indonesia extent. Rasters can be loaded directly; no conversion or further download is required.

To reproduce the official subset download into a fresh workspace, run `.venv/bin/python -m indo_data fetch --source gebco`, then `.venv/bin/python -m indo_data process --all`.

## Policy location GeoPackage

Open `data/processed/policy_treatment/2026-09-25/policy_location_proxies.gpkg` in QGIS. It contains:

| Layer | Suggested style | Meaning |
|---|---|---|
| `kapet_whole_unit_proxies` | blue outlines, transparent fill | Modern OSM polygons for explicitly whole named administrative units; **not historical treatment boundaries** |
| `kapet_review_points` | orange circles | Named partial areas or islands with a modern point anchor; no extent is inferred |
| `kek_official_reference_points` | purple diamonds | Coordinates published on official KEK detail pages; no site boundary is inferred |
| `kek_site_candidates` | purple outlines | Exact named OSM site polygons only; the layer may be empty |

Label KAPET features with `legal_name`; label KEK reference points with `legal_name`. Show `geometry_role`, `instrument`, `legal_locator`, `osm_id`, `snapshot`, and `review_note` in identify results. `policy_location_crosswalk.csv` records the source and matching rationale for every geometry. `policy_location_review.csv` lists all legal place claims, including unmatched or ambiguous ones with no geometry. These modern proxies must not be used to assign 1992–2020 KAPET treatment or national non-treatment.

OSM extracts are dated `260924` (24 September 2026) and credited **© OpenStreetMap contributors, ODbL 1.0**. Sources and SHA-256 checksums are in `config/sources.yaml` and `metadata/file_manifest.csv`.
