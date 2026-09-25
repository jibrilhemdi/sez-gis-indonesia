# Offline QA report

- Manifest: 372 paths checked for bytes and SHA-256; 0 mismatch(es).
- Indonesia ADM0: 1 valid national feature, 1,312 polygon components; small-island completeness unverified against independent coast data.
- PortWatch: 284,618 daily rows, 101 activity ports, 101 current points; 0 activity IDs without geometry, 0 points without activity; actual dates 2019-01-01 to 2026-09-18.
- PortWatch month: 9,393 rows; grain, expected days, coverage ratios, and partial flags checked.
- PortWatch year: 808 rows; grain, expected days, coverage ratios, and partial flags checked.
- BIG current inventory: 2,505 rows, valid points, unique layer/object IDs. Historical year fields audited separately.
- Historical evidence: 7 ports, 203 port-years; post-1995 states unknown and geometry unassigned.
- BIG supplementary peat: 146 valid regional polygons, bounds (108.86, -3.461, 118.576, 4.07); no national non-peat inference.
- OSM coastline: 22,086 valid regional lines; country attribution unresolved.
- GEBCO elevation: 5040 × 12000, EPSG:4326, int16, min=-9715, max=4686, nodata=None.
- GEBCO tid: 5040 × 12000, EPSG:4326, uint8, min=0, max=70, nodata=None.
- KAPET: 14 documented designation candidates; no treatment polygons or national non-treatment labels.
- KEK: 2 unique official detail records; legal dates blank and geometry unverified; national completeness not asserted.
- Policy location GIS: 32 valid modern proxy features in four layers; 72 legal/site review rows, including unresolved claims; no historical treatment labels.
- Manual evidence: 96 distinct claims with source, locator, and review status.
- SKIPPED peat raster mask/class QA: CIFOR raster and verified legend were not acquired; no binary mask was created.
- SKIPPED historical port crosswalk ambiguity QA: no automated cross-source match was accepted; all candidates remain in review queues.
- SKIPPED KAPET/KEK polygon overlap QA: no legally verified treatment boundaries were acquired.

Failures: 0.

