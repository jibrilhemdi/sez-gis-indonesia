# Data collected

**An inventory of what is actually on disk**, one entry per dataset: what it is, what is
inside it, and what it can be used for in this project.

## How this differs from `data-register.md`

The two files answer different questions and it is worth keeping them apart.

- **`data-register.md`** is about *acquisition*: where a dataset came from, which epoch and
  licence it carries, how to query the server, what to download next and in what order.
- **`data-collected.md`** (this file) is about *use*: given that the file is now sitting in
  `data/raw/`, what is it, and which part of the analysis can it feed?

The register is written at download time and answers "can I trust this?". This file answers
"what do I do with it?". A dataset appears in both.

Cross-references like *(considerations M7)* point at entries in `docs/considerations.md`.

---

## Summary

| Group | Datasets | On disk |
|---|---|---|
| Agglomeration, built-up, population — **1990–2020** | 4 GHSL products × 7 epochs (504 tiles) | 1.8 GB raw (+1.8 GB extracted) |
| Contemporary, exploratory | 3 GHS-WUP + WorldPop | 1.8 GB |
| Terrain | 1 (Copernicus GLO-90, 467 tiles) | 1.1 GB |
| Transport network | 1 (BIG) | 42 MB |
| Water | 5 (BIG) | 27 MB |
| Coast and land | 2 (BIG) | 18 MB |
| Reference / metadata | 1 (BIG sheet index) | 1 MB |

**Total ~7 GB.** Paths follow the repository layout `data/raw/<source_id>/<retrieval batch>/`;
`data-register.md` §1 has the full path of every file.

### What changed on 2026-10-07

The first downloads (September) were global GHSL files at 2018, 2025 and 2030 — taken to see
what the products look like, and none usable in the model, because the design measures
predictors circa 1992–2000 and the outcome over 1992–2020 (`proposal.md` §6.2, considerations
D1). They also filled the disk: 104 GB, one 10 m file alone 83 GB. They have been replaced by
the **multi-epoch series in §1**, taken as Indonesian tiles only, at 100 m — 1.8 GB for 28
product-epochs, against 83 GB for one. That is considerations D10, now closed.

---

# 1. Agglomeration, built-up and population

## 1.1 The GHSL R2023A series, 1990–2020 — what the model can use

`data/raw/ghsl_<product>_r2023a/2026-10-07_tiles/` — 18 tiles × 7 epochs per product, as zips.
`data/interim/ghsl/GHS_<product>_E<epoch>_…_IDN18.vrt` — one virtual mosaic per product × epoch.

**Open the `.vrt`, not the tiles.** A VRT is a few kB of XML that tells GDAL "this raster is
these 18 files side by side"; rasterio, QGIS and geopandas-adjacent tools open it as one image.
Rebuild with `scripts/build_ghsl_mosaics.py` (seconds) if `data/interim/` is ever lost.

| Product | Unit per cell | Resolution | dtype / nodata | Role |
|---|---|---|---|---|
| **BUILT-S** | m² of roof (max 10,000) | 100 m | uint16 / 65535 | Outcome robustness proxy; pre-period existing development |
| **BUILT-V** | m³ of building | 100 m | uint32 / 4294967295 | Candidate industrial-vs-commercial discriminator |
| **POP** | residents | 100 m | float64 / −200 | Labour pool (Marshall's matching) |
| **SMOD** | class 10–30 | 1 km | int16 / −200 | Descriptives and masking only |

All are Mollweide (ESRI:54009), an equal-area projection — the right one for summing areas and
counts into grid cells. The BIG vectors are EPSG:4326; everything has to meet in one CRS before
any overlay, and that choice is still open. (The shared pipeline's `config/project.yaml`
proposes EPSG:6933, also equal-area.)

**The epochs and the design.** 1990, 1995, 2000 are the **pre-period** — the predictors.
2005, 2010, 2015, 2020 are the **outcome window**. Which epoch ends the predictor window is a
decision, not a fact: see considerations M5 — predictors and outcome must not overlap, and GHSL
moves in 5-year steps, so "1992–2000" in the proposal really means "1990 + 1995" or "1990 +
1995 + 2000", and those are two different papers.

**How each can be used.**

- **BUILT-S** is the continuous built-up quantity the proposal names as the robustness
  alternative to night lights — because it can be *differenced between epochs into a growth
  trajectory*, which a class label cannot (considerations D2). Summing m² of roof into a 10 km
  cell is exact at any input resolution, which is why 100 m loses nothing against 10 m.
- **BUILT-V** ÷ BUILT-S is mean building height. Industrial estates are low-rise and
  large-footprint, commercial cores tall and small-footprint, so the ratio is a **candidate
  discriminator between industrial and commercial built-up** — some answer to considerations
  M2 (the outcome measures activity in general, not industry). Promising and untested.
- **POP** is the labour-pool layer and the population half of market access. **Caveat, and
  it is conceptual:** GHS-POP is *modelled* — census totals for an administrative unit spread
  across cells in proportion to GHSL's own built-up surface. Population and built-up are
  therefore not independent measurements; predicting a BUILT-S outcome with GHS-POP partly
  regresses a variable on a transformation of itself. For the pre-period labour layer, IPUMS
  census microdata is the more honest source (`data-register.md` §5).
- **SMOD** is a classification (30 urban centre · 23/22/21 dense / semi-dense town / suburban ·
  13/12/11 village / dispersed rural / mostly uninhabited · 10 water). Use it to describe — how
  urban was a KAPET zone when designated? — and as a cheap land/water mask. It cannot be
  differenced into growth: a jump from class 12 to 21 has no defensible value in units.

**Caveats.**

- **Not every product covers the same rectangle.** GHSL's BUILT tiles for the western column
  are cropped, so the BUILT mosaics are 57,000 cells wide and POP 60,000. Align to the analysis
  grid before comparing cell by cell.
- **On the map, growth is real but subtle.** Java was already widely settled in 1990, and the
  map's log colour scale emphasises *where* building exists more than *how much it grew*.
  Growth is better shown as a difference layer (2020 − 1990), which does not exist yet.
- **R2023A only.** Do not mix in the R2025A GHS-WUP layers (§1.2) within one variable.

## 1.2 GHS-WUP — the R2025A projection series (exploratory)

Three products, a **different release and a different product family** from the four above:

| Path | What it is | Resolution / CRS | Size |
|---|---|---|---|
| `GHS_WUP_BUILT_S_E2025_GLOBE_R2025A_4326_30ss_V1_0/` | Projected built-up surface | 30 arc-sec (~1 km), **EPSG:4326** | 360 MB + 112 MB ovr |
| `GHS_WUP_POP_E2025_GLOBE_R2025A_4326_30ss_V1_0/` | Projected population | 30 arc-sec, **EPSG:4326** | 643 MB + 201 MB ovr |
| `GHS_WUP_DEGURBA_E2025_GLOBE_R2025A_54009_1000_V1_0/` | Degree-of-urbanisation raster **plus four shapefiles** | 1 km, Mollweide | ~135 MB |

The DEGURBA folder is the interesting one, because it contains **vector delineations** rather
than only a raster:

- `..._UC_V1_0.shp` — **urban centres** (the highest density class)
- `..._DUC_V1_0.shp` — **dense urban clusters**
- `..._SDUC_V1_0.shp` — **semi-dense urban clusters**
- `..._RC_V1_0.shp` — **rural clusters**
- `..._CAPITALS_V1_0.xlsx` — capital-city attributes

**How it can be used.** The polygon delineations are far more useful than they look. A raster
tells you a cell's class; **a polygon tells you which cells belong to the same settlement**,
which is what you need to say "this is one agglomeration" rather than "these are 40 urban
cells". Concretely they support: naming and locating the corridors RQ3 is supposed to produce
(Makassar, Medan–Kuala Tanjung, Batam–Bintan); measuring distance *to the nearest urban
centre* as a predictor; and giving a settlement-level unit for descriptives that the grid
deliberately avoids for modelling.

**Caveats.**

- **R2025A is not R2023A.** They are separate releases with separate methods; mixing them
  within one variable is a silent inconsistency. Note which release each layer came from — it
  is in the filename, which is why the filenames should never be shortened.
- **These are World Urbanization Prospects *projections* for 2025** — modelled forward, not
  observed. Fine for exploring; not evidence about the past.
- Two of the three are EPSG:4326 while everything else in this folder is Mollweide. Mixing
  geographic and projected CRSs is the classic source of an area calculation that is quietly
  wrong by a latitude-dependent factor.

## 1.3 WorldPop — Indonesia (exploratory)

`data/raw/worldpop_idn/2026-09-12/`

| File | What it is | Size |
|---|---|---|
| `idn_pop_2025_CN_100m_R2025A_v1.tif` | **Constrained** population, 100 m, 2025 | 162 MB |
| `IDN_DUG_2026_GRID_L1_R2025A_v1.tif` | Degree of urbanisation, grid level 1, 2026 | 0.2 MB |
| `IDN_DUG_2026_GRID_L2_R2025A_v1.tif` | Degree of urbanisation, grid level 2, 2026 | 0.3 MB |
| `IDN_DUG_2026_entities_R2025A_v1.zip` | Named entities for the DUG grids | 1.1 MB |
| `IDN_DUG_2026_statistics_R2025A_v1.zip` | Tabular statistics for the DUG grids | 0.03 MB |

**How it can be used.** An **independent second estimate of population** against which to
check GHS-POP. That is worth having — but see the caveat, because it checks less than it
appears to.

Practically, WorldPop's advantage here is that it is distributed **per country**, so the
Indonesia file is 162 MB where the global GHSL equivalent is gigabytes. For a first look at
population structure it is much the faster route.

**Caveat.** *Constrained* means population is distributed only onto cells a built-up layer says
are settled. Both WorldPop and GHS-POP are modelled downscalings of the **same underlying
census**, so comparing them mostly compares the two downscaling methods, not the population.
Agreement is not corroboration of the count; disagreement does locate places where the
settlement layers disagree, which is itself useful.

---

# 2. Transport network

## 2.1 BIG — Jaringan Jalan (land transport)

`data/raw/big_atlas_transportasi_darat/2026-09-12/big_transportasi_darat.geojson` — **136,810 features, 41.6 MB**

| | |
|---|---|
| **Source** | `PTRA/Atlas_Transportasi_Darat` layer 1, BIG ArcGIS REST |
| **Vintage** | **2013** (RBI 1:250,000; source imagery 2008–2011) |
| **CRS** | EPSG:4326, simplified server-side at ~100 m, 6-decimal coordinates |
| **Attributes** | `OBJECTID`, `NAMA_UNSUR` (feature class), `Shape_Length` (**in degrees**) |
| **Total length** | 475,848 km, of which 469,860 km is road |

**How it can be used.** This is the network for **market access** — the most load-bearing
layer in the whole stack. Routing over it gives travel time to ports and to population, which
is the operationalisation of Marshall's *sharing* and of transport cost (considerations T2).
It is also a useful **completeness cross-check on OpenStreetMap**, whose coverage in the Outer
Islands is uneven in ways that would bias a market-access surface exactly where the KAPET
zones were.

**Class composition, measured after download:**

| Class | Features | km | % of km |
|---|---|---|---|
| *Jalan Lain* — "other" | 99,518 | 282,459 | **59.4%** |
| *Jalan Lokal* — local | 18,567 | 75,028 | 15.8% |
| *Jalan Kolektor* — collector | 3,604 | 66,164 | 13.9% |
| *Jalan Setapak* — footpath | 14,395 | 36,273 | 7.6% |
| *Jalan Arteri* — arterial | 233 | 8,622 | 1.8% |
| *Jalan Kereta Api* — railway (2 classes) | 195 | 5,717 | 1.2% |
| *Jalan Lori* — tramway/trolley road | 106 | 700 | 0.1% |
| *Jalan Tol* — toll, dual carriageway | 103 | 614 | 0.1% |
| *Landas Pacu* — airport runway (4 classes) | 89 | 271 | 0.1% |

**Three caveats, and they are all live.**

- **Filter the railways and runways before routing** (considerations M8). It is a *land
  transport* atlas, not a road atlas. Unfiltered, a routing graph will send freight down a
  runway — and runways sit at airports, adjacent to exactly the urban cells whose
  accessibility is being measured.
- **59% of length is unclassified `Jalan Lain`** (considerations M7). Only ~32% carries a class
  that maps to a speed. Whatever speed is assigned to *Jalan Lain* silently sets most of the
  country's market-access surface, and the error has a direction: guess high and remote
  districts look better connected than they are, inflating suitability exactly where KAPET
  was. Treat it as a sensitivity parameter, not a constant.
- **`Shape_Length` is in decimal degrees, not metres.** Compute lengths in a projected CRS.
- **2013 is contemporary, not pre-period** — so this does not close the gap in considerations
  I4.

---

# 3. Water

All five from BIG, all EPSG:4326, all simplified at ~100 m, all 1:250,000 (except the
bathymetry, 1:500,000).

## 3.1 Rivers — `big_250k_sungai_rivers.geojson`
**3,624 LineStrings, 8.9 MB.** `Atlas_250K_WilayahSungai` layer 3.

**Use:** surface-water availability for industrial process water; a developability constraint
(floodplain proximity); and a input to distance-to-water predictors. Rivers are also
navigable transport in parts of Kalimantan and Sumatra, which matters for market access in
places with no road.

## 3.2 Lakes and reservoirs — `big_250k_danau_lakes.geojson`
**802 Polygons, 0.8 MB.** *Danau/Waduk/Situ* — natural lakes, reservoirs and ponds.

**Use:** water supply, and part of the non-developable land mask (you cannot build on a lake).
Reservoirs specifically are a weak proxy for hydroelectric generation, which touches the power
layer the proposal calls non-negotiable — weak because the layer does not distinguish a
hydro dam from an ornamental pond.

## 3.3 River basins — `big_250k_wilayah_sungai_basins.geojson`
**9,730 Polygons, 5.8 MB.** *Wilayah Sungai* — the official river-basin territories.

**Use:** more valuable as a **spatial unit** than as a variable. Basins are a natural
hydrological region, and they make a defensible blocking structure for **spatial block
cross-validation** (considerations S1, S2) — blocks that follow a real spatial process rather
than an arbitrary square grid. They are also the administrative unit for Indonesian water
management, so they are the right join key for any water-governance data added later.

## 3.4 Groundwater potential — `big_250k_potensi_air_tanah.geojson`
**1,559 Polygons, 4.4 MB.** `Atlas_250K_Hidrogeologi` layer 8.

**Use:** a direct input to the **land, water and housing** layer of the precondition stack.
Manufacturing needs process water, and in an archipelago much of it is groundwater. This is
the closest thing on disk to a genuine industrial water-supply constraint — and it is a layer
most suitability studies of this kind do not have, so it is a small point of distinction.

**Caveat:** the attribute is a qualitative potential class, not a yield in litres per second.
It ranks places; it does not measure them.

## 3.5 Bathymetric depth areas — `big_kedalaman_depth_areas_lln500k.geojson`
**4,940 Polygons, 7.0 MB.** `PKLP/DataBatimetri_BIG_2017` layer 12, 1:500,000.

**Use:** this feeds the **natural-harbour suitability instrument** (considerations I3) — the
exogenous geography used to instrument port access. Depth polygons near a coastline are half
of what makes a natural harbour; coastline geometry (§4.1) is the other half. Being
time-invariant physical geography is exactly the property the instrument needs.

**Caveat:** 1:500,000 is coarse for harbour-scale judgements. Finer depth layers exist in the
same service (LLN 250K/50K, LPI 25K/50K/250K) if precision turns out to matter. And the
exclusion restriction remains the hard part — see I3; the data being clean does not make the
instrument valid.

---

# 4. Coast and land

## 4.1 Coastline — `big_250k_garis_pantai_coastline.geojson`
**10,765 LineStrings, 5.5 MB.** `Atlas_250K_WilayahSungai` layer 7.

**Use:** **coastal distance**, one of the natural-geography instruments (I3); coastline
geometry for natural-harbour suitability alongside §3.5; and the boundary for any
land-masking done from lines rather than polygons.

**Caveat:** includes neighbouring countries — three features named *Garis Pantai Malaka* run
up the strait into Malaysia and Thailand, reaching 7.125°N against Indonesia's northern limit
of ~5.9°N (considerations D8).

## 4.2 Land polygons — `big_area_daratan_land.geojson`
**17,257 Polygons, 12.4 MB.** `PKLP/DataBatimetri_BIG_2017` layer 8. Attributes include
`NEGARA` (country), `PROVINSI`, `TOPONIM` (place name).

**Use — this is the most immediately important vector layer on disk.** It is the **land mask**
that must exist before any analysis grid is built (considerations S3). A 10 km grid over
Indonesia is mostly sea; without a mask, the spatial weights matrix treats cells on different
islands as neighbours, which is precisely the adjacency a spatial lag model is supposed to
encode — a classic failure in coastal and island study areas. It also gives cell
land area, which is the denominator for every density measure, and `TOPONIM` gives island
names for free.

**Caveats.**

- **`NEGARA` is 17,075 Indonesia, 127 Malaysia, 28 Singapore, 27 Timor-Leste.** Which default
  is right depends on the use, and the two uses disagree (considerations D8): for the *land
  mask*, keep the foreign polygons, because excluding Malaysia puts a false coastline through
  the middle of Borneo. For anything *describing Indonesian territory*, filter. The 28
  Singapore polygons are incidentally useful — Batam's adjacency to Singapore is the anchor
  case in considerations T4.
- **One degenerate ring** (`OBJECTID 16692`): a zero-area sliver, four points on one meridian,
  about 44 cm long. Kept deliberately rather than dropped, so the feature count still matches
  the server's (considerations D7). Run `make_valid` / `.buffer(0)` before any geometric
  operation, or it will throw.

---

# 4b. Terrain

## 4b.1 Copernicus DEM GLO-90 — `copernicus_dem_glo90/2026-09-12/`

| | |
|---|---|
| **What it is** | Digital *surface* model — 467 one-degree COG tiles, 3 arc-second (~90 m), EPSG:4326, heights above EGM2008. Fetched from AWS Open Data with `scripts/fetch_terrain.py`. |
| **Vintage** | TanDEM-X acquisitions, roughly 2011–2015 |
| **Size** | 1.1 GB |
| **Licence** | Attribution **required**: "© DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved." |

**What it feeds.** Terrain ruggedness (a suitability layer *and* one of the natural-geography
instruments in considerations I3), slope for land developability, and coastal-distance and
elevation surfaces.

**The epoch exemption.** Every other layer here is checked against the 1992–2000 / 1992–2020
staging. Terrain is exempt, and deliberately: mountains do not move over a 30-year panel, and
that time-invariance is exactly what qualifies ruggedness as an exogenous instrument. Say so
in the paper, or a careful reader will apply the same epoch scepticism used everywhere else
(considerations D11).

**Verified against known summits**, which is the cheapest real check that a DEM is a DEM:

| Peak | DEM max | Published |
|---|---|---|
| Puncak Jaya, Papua | 4794 m | 4884 m |
| Kerinci, Sumatra | 3759 m | 3805 m |
| Semeru, Java | 3665 m | 3676 m |
| Rinjani, Lombok | 3687 m | 3726 m |

All 0.3–1.8% low, consistently — the expected behaviour of a 90 m grid on a sharp peak, which
averages the summit down. A DEM reading *high*, or wrong by tens of percent, would mean
something else entirely.

**Two things to handle before use.** It is a **surface** model, so it includes tree canopy and
buildings — over Kalimantan's forest that is metres of bias, and it inflates ruggedness in
forested terrain relative to cleared terrain. And values below sea level appear over water
(the Lombok tile reaches −121 m), so mask to land before computing anything.

**What is NOT here: GLO-30.** ~19 GB against 11.9 GB free (considerations D10). Ruggedness is
scale-dependent, so GLO-30 cannot simply be swapped in later — the instrument would have to be
re-estimated (D11).

# 5. Reference and metadata

## 5.1 RBI 1:250K sheet index — `big_rbi_250k_sheet_index.geojson`
**309 Polygons, 1.0 MB.** `PPIG/IDX_Download` layer 3.

**Use:** not an analysis layer — a **provenance layer**. Each polygon is one map sheet and
carries its production history: `THN_BUAT` (year made), `SBR_DATA` (source data), `METODE`,
`PELAKSANA` (contractor), and flags for which derived products exist per sheet. This is what
established that the BIG vector layers are **2013 vintage**, and what settled the terrain
question — `SBR_DATA2` reads *"ALOS-AVNIR dan Landsat TM5 tahun 2008-2011, SRTM 30m dan ASTER
DEM"*, i.e. BIG's own terrain is SRTM (considerations D6).

It is also the honest answer to "how good is this layer here?", sheet by sheet — the sort of
thing a referee asks and most papers cannot answer.

---

# 6. Superseded

Nothing. The September GHSL downloads (global files at 2018/2025/2030, and 18 SMOD 2030 tiles)
were deleted on 2026-10-07 once the multi-epoch series replaced them: all wrong-epoch, all
re-downloadable from JRC, and together they had filled the disk. The one useful thing among
them — the GHSL tile-grid shapefile — was kept and moved to `data/raw/ghsl_tile_grid/`, because
`scripts/fetch_ghsl.py` derives its tile list from it.

---

# 7. What is not collected yet

| # | Layer | Status |
|---|---|---|
| 1 | **Harmonised night lights 1992–2020** (Li et al. 2020) | **Not started. The outcome variable — no Tier 2 model can start without it.** Now the single most important download. |
| 2 | **Ports** — PortWatch, BIG/Kemenhub points, IAPH 1996 | Acquired in the shared `indo_data` pipeline (2026-09-25). |
| 3 | **Coast and bathymetry** — OSM coastline, GEBCO_2026 | Acquired in the `indo_data` pipeline. |
| 4 | **KAPET and SEZ/KEK** | Decrees transcribed and modern location proxies built in the `indo_data` pipeline; **no historical treatment geometry yet** (considerations D3). |
| 5 | **Peatland** | Partial (BIG peat soils, part of Kalimantan); CIFOR V3 needs a manual terms step. |
| 6 | **Flood hazard, JRC Global Surface Water** | Not started. |
| 7 | **IPUMS census** (pre-period labour) | Not started; free with registration. |

The pipeline's layers can be put on the map by adding entries to `config/map_layers.yaml`.

---

# 8. Adding to this file

- **One entry per dataset, written when the download lands**, alongside its row in
  `data-register.md`. The register records where it came from; this file records what it is
  for.
- **Say what it can be used for in terms of the precondition stack or a specific RQ.** "Water
  data" is not a use; "process-water availability, feeding the land/water/housing layer" is.
- **Record what a layer does *not* contain**, and what it will break if used naively. The
  caveat is usually the most valuable line in the entry — every one above was found by
  checking, not by reading documentation.
- **Never shorten a GHSL filename.** Product, epoch, release, CRS and resolution are all
  encoded in it, and it is the only place several of them are recorded.
