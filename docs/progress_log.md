# Progress log

## 2026-09-25 — environment and discovery

- Existing repository contained README, .gitignore and .git only; no pipeline.
- macOS arm64, Python 3.14.6; approximately 112 GiB free. Default shell DNS was denied; approved elevated shell access succeeded for public URLs.
- Created local `.venv` and installed dependencies. Exact versions are in `docs/dependency_versions.txt`.
- Verified geoBoundaries ADM0 API, PortWatch ArcGIS daily and ports layers, and BIG MapServer metadata. PortWatch filtered count at discovery: 284,618 Indonesia daily records from requested start; this is a discovery count and can change before acquisition.
- CIFOR V3 download requires guest-book and terms acceptance; manual review needed.
- GEBCO's live official release page advertises GEBCO_2026; the earlier 2025 search snippet was stale. Configuration was corrected before any GEBCO download.

## 2026-09-25 — acquisition and processing

- Downloaded geoBoundaries Indonesia ADM0 GeoJSON; 2017 represented year, valid multipolygon, 1,312 components. Small-island completeness needs an independent check.
- Acquired 284,618 Indonesia PortWatch daily records, actually dated 2019-01-01 through 2026-09-18, and 101 companion points. Frozen ID lists, raw ArcGIS batches, layer metadata, and count/edit checks were retained. Produced daily/monthly/yearly Parquet and point GeoPackage.
- Acquired 527 BIG/Kemenhub public-port points and 1,978 special terminals. Year fields were mostly sentinels; kept all 2,505 current points as current-location proxies and put records in a review queue.
- Downloaded the June 1996 IAPH PDF. Table 3.3 supports presence for seven named ports in 1991–1995. Produced 35 event rows and a 203-row annual table; unsupported years remain unknown. OCR errors prevented reliable quantity transcription.
- Downloaded the processed OSM coastline archive and clipped 22,086 valid regional lines. Kept neighbouring coasts as context without assigning country labels.
- Acquired official CEDA GEBCO_2026 elevation and TID native-resolution subsets (5,040 × 12,000 each). Kept raw NetCDF and generated aligned north-up GeoTIFFs. Confirmed sample values against the remote grid.
- CIFOR Global Wetlands V3 required a guest book/terms action and was not downloaded. Acquired 146 public BIG peat-soil polygons as a regional supplement, without calling uncovered areas non-peat.
- Direct shell access to official KAPET decrees failed (BPK Cloudflare 403; PDF host timeout). Indexed official decree text supports five designation candidates and three programme events, but territory, dates and geometry remain incomplete. Two official KEK detail pages were acquired separately.
- Acquired the published 2025 Rothenberg–Wang–Chari article PDF from the University of Sussex repository. Native text on PDF page 22 states that data will be available on request. The author's publication page has no linked replication package for this specific paper; the nearby packages are for different articles. No treatment geometry was obtained.

## 2026-09-25 — QA and delivery

- Reopened vectors, rasters and tables, checked raw/derived manifest checksums, ArcGIS IDs, grains, join coverage, geometry and temporal states. Updated acquisition/QA reports, rights notes, review queue, data dictionary and README.
- The verified data support contemporary port and coast/bathymetry research inputs plus a small dated port subset. National peat extent, historical port geometry, and historical KAPET treatment geography remain unresolved. No final suitability surface or policy treatment overlay was produced.

## 2026-09-25 — GEBCO use and policy-location GIS

- Confirmed the Indonesia GEBCO elevation and TID rasters are ready to open directly in QGIS; added styling and interpretation guidance in `docs/qgis_gebco_policy.md`.
- Reviewed official designation articles for 14 KAPET instruments, plus the Biak and programme amendments. Transcribed 70 named place claims, retaining article references and uncertainty about missing annex maps. The Benaviq decree concerns historical Timor Timur and is outside the present Indonesia extract.
- Acquired six pinned Geofabrik `260924` OSM GeoPackage archives (2,196,215,457 compressed bytes) and registered source HEAD metadata, SHA-256 checksums, and expanded files. Matched names against OSM administrative level, region and province. Ambiguous Bima and historical Pontianak/Kendari identities remain unresolved.
- Created `policy_location_proxies.gpkg` with 16 modern KAPET whole-unit polygons, 12 KAPET review points, two exact named KEK OSM site candidates, and two official KEK reference points. All 70 KAPET place claims and two KEK site checks remain in `policy_location_review.csv`; the crosswalk records legal and OSM provenance. These features are contemporary cues, not historical treatment polygons.
- Added `fetch --source osm_policy`, QGIS map legend, source catalog, rights and temporal notes, global review queue entries, and focused matching tests. Full offline validation passed with zero failures; eight tests passed.
