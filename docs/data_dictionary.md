# Data dictionary and interpretation

## PortWatch daily activity

Grain: one PortWatch `portid` per `date`. `source_object_id` retains ArcGIS `ObjectId`. `port_id` is the original stable source ID; `port_name_original` preserves `portname`. The raw response keeps every source field. Processed daily columns `portcalls`, `import`, `export`, and their vessel-type components retain source names. `portcalls*` are reported calls, not unique vessel counts. `import*` and `export*` are AIS-derived shipment estimates in metric tons, not customs declarations, monetary value, or TEU. The IMF methodology describes arrivals/departures and shipment estimation from vessel payload and deadweight tonnage. A total is never added to its component fields.

Monthly and yearly tables sum each additive source measure independently with `min_count=1`; all-missing groups stay missing. `observed_days` counts distinct dates with a row, while each `<measure>_missing_days` counts days without a reported value, including absent calendar days. `expected_calendar_days` uses the actual month/year including leap days. `coverage_ratio` is observed days divided by expected days. `partial_period` is true whenever observed days are fewer than expected. No incomplete period is extrapolated.

The processed PortWatch point layer is a current reference inventory. Point geometry is not historical evidence. The `vessel_count_*` fields are source-provided yearly averages over the publisher's stated observation span and are not daily port calls.

## BIG/Kemenhub ports

`source_layer_id=1` denotes public ports; `3` denotes special terminals. Original `namobj`, `objectid`, `kode`, `thn_bng`, `thn_kmb`, `thn_ops`, and `stat_ops` remain in the current inventory. The year fields are audited for plausible numeric values; they are not treated as original opening years without decree/port-history review. `geometry_role=current_location_proxy`, blank geometry vintage, and `location_stability=unverified` prevent backdating the points.

## Boundary and coastline

geoBoundaries ADM0 is a national selection reference with the source's represented year, not an exact or historical shoreline. The processed OSM coastline is regional current geometry including neighbouring coasts. `context_role=regional_coast_unclassified` makes country attribution explicit. It is a candidate geography input, not a proved natural-harbour instrument.

## Peat, bathymetry, and policy

CIFOR peat extent, if imported, requires publisher legend review before `1=peat, 0=known non-peat, unknown=nodata` can be derived. The acquired BIG peat-soil polygons cover only part of Kalimantan; their absence elsewhere means unknown coverage, not known non-peat. GEBCO signed elevation is metres; negative values are bathymetric depths and TID is categorical source provenance. Policy dates and territories remain evidence-specific; no absent registry row implies non-treatment.

`policy_location_proxies.gpkg` stores dated modern location cues in four layers: `kapet_whole_unit_proxies` (modern OSM administrative polygons for whole named legal units), `kapet_review_points` (point anchors for partial or island claims), `kek_site_candidates` (exact named OSM site polygons, requiring location and scale checks), and `kek_official_reference_points` (coordinates from official KEK detail pages). Each feature has `geometry_role=current_location_proxy`. `policy_location_crosswalk.csv` records legal place claim, article, OSM feature ID, snapshot and match rationale. `policy_location_review.csv` retains every legal/site claim, including unmatched names and historical Timor Timur. None of these fields is a treatment status or historical boundary.
