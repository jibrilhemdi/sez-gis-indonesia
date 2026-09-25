# Acquisition report

Run date: 2026-09-25. Scope: five research groups plus ADM0 and dated OSM policy-location support. Status is based on the files and checks below.

| Source | Acquisition | Detail |
|---|---|---|
| big_kemenhub_ports | partial | Current inventory verified; historical presence and geometry unresolved |
| big_kemenhub_ports_1 | verified | ArcGIS ID and count reconciliation |
| big_kemenhub_ports_3 | verified | ArcGIS ID and count reconciliation |
| big_peta_lahan_gambut | partial | Verified supplementary government peat polygons; only regional coverage, not CIFOR substitute |
| cifor_global_wetlands_v3 | manual_required | CIFOR guest book and terms require human action |
| gebco_2026 | verified | Native-resolution elevation and TID GeoTIFFs reopened; signed elevation and TID categories retained |
| geoboundaries_idn_adm0 | verified | ADM0 GeoJSON reopened and valid; national selection boundary |
| geofabrik_osm_policy | verified | Six dated OSM extracts matched to legal place claims; modern proxy GIS and unresolved queue produced |
| iaph_ports_harbors_1996_06 | partial | Seven ports documented in 1991–1995 table; current identity and historic geometry unresolved |
| imf_portwatch_daily | verified | Daily, monthly, annual tables processed |
| imf_portwatch_ports | verified | ArcGIS IDs reconciled; 101 current points reopened as valid geometry |
| jdih_bpk_keppres_89_1996 | access_denied | BPK legal page returned Cloudflare 403; official peraturan.go.id PDF host timed out in shell. Indexed official text supports partial claims, but native PDFs were not acquired. |
| kek_official_registry | partial | Official KEK detail pages verified; registry incomplete, no legal dates or polygons |
| official_kapet_decrees | partial | Fourteen source-backed designation instruments; named places recorded; annex and historical geometry incomplete |
| osmdata_coastlines | partial | Regional processed coastline verified; country segment attribution unresolved |
| rothenberg_wang_chari_2025 | verified | Published PDF reopened; data availability statement on page 22: available on request |

Manifest: 372 files, 8,743,758,234 bytes (raw and derived; checksums in metadata/file_manifest.csv).

## Group results

### Peatland — partial; preferred raster requires manual access

- Obtained: BIG/Kementerian Pertanian *Peta Lahan Gambut* public MapServer layer 6, 146 valid soil polygons in a Kalimantan-only extent (108.86–118.58°E, 3.46°S–4.07°N). Raw ArcGIS responses and `data/processed/peatland/2026-09-25/big_peta_lahan_gambut_partial.gpkg` are recorded in the manifest.
- Usable role: supplementary regional peat-soil evidence. Outside these polygons and the service extent remains unknown. This does not yield a national peat or non-peat mask, and the map has no verified 1992 vintage.
- CIFOR Global Wetlands V3 peat-extent raster was not acquired because its guest book and terms require human review. See `docs/manual_actions.md`; inspect the exact product legend and rights before any canonical mask.

### Port activity — acquired and validated for contemporary use

- Obtained: IMF PortWatch `Daily_Ports_Data` Indonesia extract, 284,618 unique port-date records across 101 ports, actually observed 2019-01-01 through 2026-09-18; 101 companion current points. Outputs are daily (284,618 rows), monthly (9,393), and annual (808) Parquet plus GeoPackage under `data/processed/port_activity/2026-09-25/`.
- Validation: ArcGIS IDs/counts and edit timestamp reconciled; no duplicate keys or missing point joins; month/year calendar coverage and missingness checked. Port calls and shipment estimates retain publisher meanings and units. Incomplete periods are flagged, not extrapolated.
- Usable role: contemporary activity only. It does not measure 1992–2000 port throughput; points are not assigned historical geometry.

### Historical ports — current inventory plus limited dated evidence

- Obtained: BIG/Kemenhub public ports layer 1 (527 points) and special terminals layer 3 (1,978), 2,505 current points total. The year-field audit found only two plausible values in each of three fields for public ports; the other 525 values were `0`. All 1,978 terminal entries were `-` in each field. The field meanings are not enough to establish openings.
- Obtained: International Association of Ports and Harbors, *Ports and Harbors*, June 1996, PDF page 21 / printed page 19, Table 3.3. Positive 1991–1995 container entries document seven named ports in 1992 and 1995. Outputs: 35 event rows and 203 port-year rows through 2020; all post-1995 presence is `unknown`. Quantities were withheld because PDF text extraction has errors.
- Usable role: seven evidence-supported historical presences without historical coordinates; current BIG points are separate location proxies. The 2000 reference year, identity crosswalk, location stability, and national completeness need review.

### Coast and bathymetry — acquired and validated as current geography

- Obtained: processed OSM coastline ZIP snapshot dated 2026-09-25 and 22,086 valid clipped regional lines in `regional_coastline.gpkg`; it includes neighbouring coasts and has no reviewed country segment labels.
- Obtained: GEBCO_2026 official CEDA OPeNDAP regional elevation and Type Identifier subsets, both 5,040 × 12,000 native 15 arc-second cells over 93–143°E, 13°S–8°N. Raw NetCDF and source metadata plus separate north-up GeoTIFFs are retained. Elevation is signed metres; TID is categorical. Extents, CRS, shape, and sampled values were checked.
- Usable role: current coast and candidate natural-geography inputs. Reclamation, dredging, survey vintages, TID quality, and coastline country attribution need interpretation before a historical harbour instrument is claimed.

### Policy treatment — partial evidence; no verified treatment geometry

- KAPET: 14 official designation instruments and 70 named whole units, partial units, districts and islands are transcribed with article references in `kapet_registry.csv` and `kapet_place_claims.csv`. The 1998 Benaviq designation names places in historical Timor Timur, outside current Indonesia. Missing decree maps and administrative changes remain explicit. `treated_status` and historical geometry remain `unknown`.
- Dated Geofabrik OSM GeoPackages for Sumatra, Kalimantan, Sulawesi, Papua, Maluku and Nusa Tenggara (`260924` snapshot) were downloaded, checksum registered and processed. `policy_location_proxies.gpkg` has four QGIS layers: 16 modern whole-unit KAPET polygons, 12 KAPET review points, two KEK exact named OSM site polygon candidates, and 2 official KEK reference points. These are current location proxies only. `policy_location_crosswalk.csv` records legal and OSM identifiers; `policy_location_review.csv` retains all 72 legal/site review rows, including unresolved ones.
- KEK: two official detail records (Palu, manufacturing, PP 31/2014; Nongsa, service, PP 68/2021) are in a separate partial registry. Exact named OSM site polygons are candidates, not official boundaries. Legal effective dates and official site boundaries remain unverified. The official API requires authorization; no credentials were used.
- The published 2025 KAPET evaluation PDF was acquired from the University of Sussex repository. Its Data availability statement says data will be available on request (PDF page 22); this does not establish an open replication package or usable boundary geometry. The author publication page links replication packages for other papers, but none for this article at the time checked.
- Official KAPET decree article text was reviewed through indexed official PDFs, but full annex maps and some effective dates were unavailable. Import original decrees using `docs/manual_actions.md`, resolve boundaries and legal timing, and verify any subsequently obtained replication geometry before using treatment in the 1992–2020 panel.

### Supporting boundary

- geoBoundaries gbOpen Indonesia ADM0 GeoJSON represented year 2017, one valid multipolygon with 1,312 components. It is a national selection reference only; independent small-island completeness and historical administrative equivalence remain unverified.

## Reproduce and review

- Online sequence: `.venv/bin/python -m indo_data discover`, then `fetch --all`, `process --all`, `validate`, and `report`. Repeated fetches reuse unchanged local snapshots after integrity checks; changed upstream vintages are stored separately where the service supplies a version.
- Offline checks: `.venv/bin/python -m indo_data validate` and `.venv/bin/python -m indo_data report`. Inspect `reports/qa_report.md`, `reports/temporal_compatibility.csv`, `reports/review_queue.csv`, `metadata/source_catalog.csv`, and `metadata/file_manifest.csv`.
- QGIS styling and interpretation: `docs/qgis_gebco_policy.md`. Manual actions: `docs/manual_actions.md`. Rights review: `metadata/licenses/rights_review.md`.

QA figures: reports/figures/portwatch_current_points.png, reports/figures/government_peat_partial_coverage.png, reports/figures/coast_gebco_extent.png, reports/figures/policy_location_proxies.png
