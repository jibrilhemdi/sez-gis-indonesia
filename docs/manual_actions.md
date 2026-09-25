# Manual actions

## CIFOR Global Wetlands V3 peat extent

Visit [the platform](https://www2.cifor.org/global-wetlands/), follow Download to the CIFOR data page, inspect the exact product, version, legend, and terms. Its guest book and terms must be handled by a person. If permitted, download the original peat-extent GeoTIFF or archive, keep its documentation, and place both in `data/manual/peatland/`. Then run `python -m indo_data ingest-manual --theme peatland --path data/manual/peatland/<filename>`. Do not import peat depth as peat extent. This import validates raster readability and records its checksum; a canonical mask requires reviewed class meanings.

## GEBCO regional subset

The GEBCO_2026 regional elevation and TID grids have been acquired through the verified CEDA OPeNDAP route. If that route fails on rerun, use the [GEBCO download app](https://download.gebco.net/downloads) to select longitude 93–143°E and latitude 13°S–8°N, the matching elevation and TID grids. Save original files and documentation under `data/manual/coast_bathymetry/`; import each with `ingest-manual --theme coast_bathymetry`. Do not download the multi-gigabyte global grid merely to work around the app.

## Policy evidence

The KAPET register now transcribes 14 official designation articles and 70 named place claims. Use the linked official legal pages and `policy_location_review.csv` to obtain missing annex maps and confirm effective dates, later amendments and historical administrative boundaries. Preserve original PDFs under `data/manual/policy_treatment/`, then import them. For KEK, verify official site maps and regulation dates. The dated OSM policy GeoPackage is a present-day location reference only; it cannot assign historical treatment or non-treatment.
