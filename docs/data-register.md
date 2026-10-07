# Data register

What has been downloaded, where it came from, and what it is actually good for.
Supersedes the original `sezgisdata/data.md`; every source and every question from that
file is carried forward below.

**Companion file:** `docs/data-collected.md` is the inventory of what is on disk and what
each dataset is *for*. This file answers "where did it come from and can I trust it?"; that
one answers "what do I do with it?". A dataset belongs in both.

**Why a register and not a folder listing.** A raster on disk does not tell you its epoch,
its licence, or which row of the proposal's Tier A table it is meant to fill. Three months
from now, "which file is the outcome variable?" has to be answerable without re-downloading
anything. That is what this file is for — one row per dataset, and the row is written *when
the download happens*, not afterwards.

---

## 1. On disk now

**Folder layout.** Every dataset lives at `data/raw/<source_id>/<retrieval batch>/`, the
convention of the shared repository (`AGENTS.md`). The batch folder starts with the retrieval
date, so the path itself records *when* a file was taken — which is the first thing to know
about any layer whose content changes over time. Files keep the name the provider gave them.
(Reorganised into this layout on 2026-10-07; the files themselves were not changed.)

### GHSL multi-epoch series, fetched 2026-10-07

The pre-period and outcome layers. Four products of release **R2023A** × seven epochs, as the
18 GHSL tiles `R9–R11 × C28–C33` (Mollweide, ESRI:54009) that cover Indonesia — only 15 of
them contain Indonesian land; the other 3 are taken so each epoch forms one rectangle.

| Path | Product | Epochs | Resolution | Size |
|---|---|---|---|---|
| `data/raw/ghsl_built_s_r2023a/2026-10-07_tiles/` | GHS-BUILT-S — built-up surface (m² per cell) | 1990, 1995, 2000, 2005, 2010, 2015, 2020 | 100 m | 126 zips |
| `data/raw/ghsl_built_v_r2023a/2026-10-07_tiles/` | GHS-BUILT-V — built-up volume (m³ per cell) | same | 100 m | 126 zips |
| `data/raw/ghsl_pop_r2023a/2026-10-07_tiles/` | GHS-POP — residential population | same | 100 m | 126 zips |
| `data/raw/ghsl_smod_r2023a/2026-10-07_tiles/` | GHS-SMOD — degree of urbanisation (classes) | same | 1 km | 126 zips |

**Total 504 zips, 1.8 GB.** Fetched with `scripts/fetch_ghsl.py`, which derives the tile list
from the land polygons and the GHSL tile grid rather than from a list typed by hand. Each zip
is verified twice: byte size equal to the server's `Content-Length`, and every member passing
its CRC check. sha256 per file in `metadata/manifests/ghsl_tiles.csv`.

**How they were obtained, honestly stated.** 489 were downloaded by hand in a browser and
imported by the script; **15 browser downloads had silently failed** — a stub `.zip` next to a
stalled `.zip.part`, which looks like a finished file in a folder listing — and the script
fetched those 15 from JRC directly. The script alone reproduces all 504.

**Licence:** free to use with attribution — European Commission, Joint Research Centre (JRC).

**Derived:** `scripts/build_ghsl_mosaics.py` extracts the GeoTIFFs to
`data/interim/ghsl/tiles/` and writes one virtual mosaic (`.vrt`) per product × epoch to
`data/interim/ghsl/` — 28 files. The BUILT products cover 57,000 × 30,000 cells and POP
60,000 × 30,000: GHSL's tiles for the BUILT layers are cropped at the western edge of the
block, so the mosaics are not all the same extent. Align them to the analysis grid before
comparing cell by cell.

**Sanity check, 2026-10-07:** within 15 km of the centres of Jakarta, Surabaya and Batam,
BUILT-S, BUILT-V and POP rise in every one of the seven epochs. Batam goes from 12 to 37 km²
of built-up surface and from 0.1 to 1.4 million people between 1990 and 2020 — the right
order of magnitude for a city built around a 1970s–80s special zone.

### Contemporary layers (exploratory)

| Path | Dataset | Epoch | Resolution | Size |
|---|---|---|---|---|
| `data/raw/ghsl_wup_r2025a/2026-09-12/` | GHS-WUP BUILT-S, POP, DEGURBA (+ settlement polygons), release **R2025A** | **2025** (projection) | 30″ / 1 km | ~1.6 GB |
| `data/raw/worldpop_idn/2026-09-12/idn_pop_2025_*` | WorldPop constrained population, Indonesia | **2025** | 100 m | ~190 MB |
| `data/raw/worldpop_idn/2026-09-12/IDN_DUG_2026_*` | WorldPop Degree of Urbanisation, 2 grid levels + entities + statistics | **2026** | 1 km | ~15 MB |
| `data/raw/ghsl_docs/2026-09-11/GHSL_Data_Package_2023.pdf` | GHSL R2023A product documentation | — | — | 15 MB |
| `data/raw/ghsl_tile_grid/2026-09-11/` | GHSL tile grid (shapefile), used by `fetch_ghsl.py` | — | — | <1 MB |

None of these can enter the model (wrong epoch); they are kept for orientation and for RQ3.

**Removed 2026-10-07:** the global GHSL files taken earlier to look at the products —
BUILT-S 2018 at 10 m (83 GB with its overviews), BUILT-V 2030, POP 2030, SMOD 2030, and 18
SMOD 2030 tiles. All were wrong-epoch and all can be re-downloaded from JRC; they were deleted
to free the disk (considerations D10).

### BIG vector layers, fetched 2026-09-12

All via `scripts/fetch_big.py`, all EPSG:4326, all simplified server-side at
`maxAllowableOffset=0.001` (~100 m) with 6-decimal coordinates — see §4.3 for why, and
§4.4 for what that costs. Every file's feature count was verified against the server's
own `returnCountOnly` total.

| Path | Layer | Features | Size |
|---|---|---|---|
| `data/raw/big_atlas_transportasi_darat/2026-09-12/big_transportasi_darat.geojson` | `PTRA/Atlas_Transportasi_Darat/1` — *Jaringan Jalan* | 136,810 | 41.6 MB |
| `data/raw/big_atlas_250k_wilayah_sungai/2026-09-12/big_250k_sungai_rivers.geojson` | `Atlas_250K_WilayahSungai/3` — *Sungai* (rivers) | 3,624 | 8.9 MB |
| `data/raw/big_atlas_250k_wilayah_sungai/2026-09-12/big_250k_danau_lakes.geojson` | `/8` — *Danau/Waduk/Situ* (lakes, reservoirs) | 802 | 0.8 MB |
| `data/raw/big_atlas_250k_wilayah_sungai/2026-09-12/big_250k_wilayah_sungai_basins.geojson` | `/9` — *Wilayah Sungai* (river basins) | 9,730 | 5.8 MB |
| `data/raw/big_atlas_250k_hidrogeologi/2026-09-12/big_250k_potensi_air_tanah.geojson` | `Atlas_250K_Hidrogeologi/8` — *Potensi Air Tanah* (groundwater potential) | 1,559 | 4.4 MB |
| `data/raw/big_databatimetri_2017/2026-09-12/big_kedalaman_depth_areas_lln500k.geojson` | `PKLP/DataBatimetri_BIG_2017/12` — depth areas, 1:500K | 4,940 | 7.0 MB |
| `data/raw/big_atlas_250k_wilayah_sungai/2026-09-12/big_250k_garis_pantai_coastline.geojson` | `Atlas_250K_WilayahSungai/7` — *Garis Pantai* (coastline) | 10,765 | 5.5 MB |
| `data/raw/big_databatimetri_2017/2026-09-12/big_area_daratan_land.geojson` | `PKLP/DataBatimetri_BIG_2017/8` — *Area Daratan* (land polygons) | 17,257 | 12.4 MB |
| `data/raw/big_rbi_index/2026-09-12/big_rbi_250k_sheet_index.geojson` | `PPIG/IDX_Download/3` — RBI 1:250K sheet index | 309 | 1.0 MB |

**Vintage: 2013** for the RBI 1:250,000 series — every one of the 309 index sheets reports
`THN_BUAT` (year made) = 2013, derived from source imagery of 2008–2011. *Licence: not
stated on the service; see §4.5 — unresolved, and it matters.*

### ⚠️ Two things to understand about these files before using them

**(1) The BIG layers, like everything taken before 2026-10-07, are contemporary. The project
needs a 1992–2020 panel.** The proposal's design rests on measuring predictors in a **pre-period
(circa 1992–2000)** and the outcome **over 1992–2020** — that is the whole answer to reverse
causality (§6.2 of `proposal.md`). A 2030 projection and a 2025 population grid cannot
measure either. They are not wrong files; they are the wrong *epochs*, and the fix is cheap
because GHSL ships the same products for every 5-year epoch from 1975.

This also answers the first question in the original `data.md` — *"year?"*. The year is not a
detail to settle later. It is the variable the design turns on.

**(2) SMOD is a classification, not a quantity.** GHS-SMOD ("Degree of Urbanisation") labels
each cell into a class — 30 urban centre, 23/22/21 dense town / semi-dense town / suburban,
13/12/11 village / dispersed rural / mostly uninhabited, 10 water. That is a useful
*descriptive* and *masking* layer: it defines what counts as already-urban, and it is how you
exclude water cells from the grid. It is **not** the "GHSL built-up" layer the proposal names
as the robustness alternative to night lights. That is **GHS-BUILT-S** — built-up *surface*,
square metres of roof per cell — a continuous quantity you can compute a growth trajectory
from. You cannot compute a trajectory from a class label without deciding that a jump from
class 12 to class 21 is some number of units of growth, which is a decision you do not want
to have to defend.

So: SMOD is worth keeping, for the mask and for descriptives. BUILT-S is the one the
modelling needs.

### Copernicus DEM GLO-90, fetched 2026-09-12

| | |
|---|---|
| **Path** | `data/raw/copernicus_dem_glo90/2026-09-12/` |
| **Source** | AWS Open Data, bucket `copernicus-dem-90m` — no credentials, no login |
| **Product** | Copernicus DEM GLO-90, 3 arc-second (~90 m), EPSG:4326, COG GeoTIFF, one file per 1° tile |
| **Acquisition vintage** | TanDEM-X, roughly **2011–2015** |
| **Extent** | 467 tiles covering Indonesian land, derived from the `Area Daratan` polygons rather than a bounding box |
| **Licence** | Free to use **with attribution**. The required credit is: *"© DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved."* Put it in the paper's data statement — this is a real condition, not a courtesy. |

**Why Copernicus and not BIG or SRTM.** BIG publishes no DEM through its REST services, and
its own RBI sheets record their source as *"SRTM 30m dan ASTER DEM"* — the national product is
the global product reprocessed (§4.6, considerations D6). SRTM via USGS/Earthdata needs an
account; Copernicus on AWS needs nothing.

**Why GLO-90 and not GLO-30.** GLO-30 for the same tile set is about **19 GB** and the disk had
11.9 GB free (considerations D10). GLO-90 is **1.12 GB**. Defensible at a 10 km unit of
analysis, but forced by storage — and note that ruggedness is *scale-dependent*, so the
resolution is part of the variable's definition and GLO-30 cannot simply be swapped in later
(considerations D11).

**This is the one layer whose epoch does not matter.** A 2011–2015 vintage is contemporary,
not pre-period, and that is fine because terrain is time-invariant over a 30-year panel —
which is exactly the property that makes ruggedness usable as an exogenous instrument.

**Tile selection is not a bounding box.** A box around Indonesia is 782 one-degree cells and
mostly sea. `scripts/fetch_terrain.py` derives the list from the land polygons already on
disk, by two tests that catch different things — cells holding a polygon *vertex* (coastlines
and small islands) and cells whose *centre* falls inside land (the interiors of big islands,
which contain no coastline vertices at all). Vertices alone would have missed central Borneo,
Sumatra and Papua: large, mountainous, and exactly where ruggedness matters most.

Seven further cells are enclosed on all four sides by land cells — the Flores, Banda and
Molucca seas. Copernicus publishes **no tile** for any of them, which is independent
confirmation that they are open water rather than gaps in the land layer.

---

## 2. What to download next, in priority order

Priority is set by what blocks the most: the outcome variable blocks every model, so it is
first even though it is the least bureaucratic download on the list.

| # | Layer | Dataset and route | Why this one |
|---|---|---|---|
| 1 | **Outcome — agglomeration trajectory** | Harmonized DMSP-OLS + VIIRS night lights (Li et al. 2020), Figshare | The dependent variable. 1992–2020 at ~1 km, already harmonised across the two sensors, which is the hard part. Nothing in Tier 2 can start without it. |
| ~~2~~ | ~~**Built-up, multi-epoch**~~ | **DONE 2026-10-07** — GHS-BUILT-S and BUILT-V R2023A, 1990–2020. See §1. | |
| ~~3~~ | ~~**Population, multi-epoch**~~ | **DONE 2026-10-07** — GHS-POP R2023A, 1990–2020 (plus GHS-SMOD). See §1. | |
| 4 | **Roads** | OpenStreetMap, Geofabrik Indonesia extract | The network for market-access computation. See §4 on why BIG is a cross-check rather than the source. The `indo_data` pipeline has already taken pinned Geofabrik extracts (2026-09-24) for its KAPET name matching — check whether they can serve here before downloading again. |
| ~~5~~ | ~~**Terrain**~~ | **DONE 2026-09-12** — Copernicus GLO-90, 467 tiles, 1.12 GB. See above. | |
| 6 | **Coast & bathymetry** | **In the `indo_data` pipeline** — OSM coastline and GEBCO_2026, acquired 2026-09-25 | Natural-harbour suitability, the other instrument. |
| 7 | **Water & flood** | JRC Global Surface Water; a global flood-hazard layer | Land developability. Not yet acquired by anyone. |
| 8 | **Ports** | **In the `indo_data` pipeline** — IMF PortWatch daily (2019–), BIG/Kemenhub port points, IAPH 1996 table | Port access. Note the vintage split is deliberate, not a compromise. |
| 9 | **Policy treatment** | **In the `indo_data` pipeline** — KAPET decrees transcribed, modern location proxies | The KAPET indicator *is* the validation test. Still no historical treatment geometry; see below. |
| 10 | **Peatland** | **Partly in the `indo_data` pipeline** — BIG peat-soil polygons (part of Kalimantan only); CIFOR V3 needs a manual terms step | Developability constraint, and specific to Indonesia in a way reviewers will expect to see. |

**On #9.** Every other row is a file on a server. KAPET boundaries may have to be
reconstructed from the decrees that designated the zones (a list of districts, in *1990s*
district boundaries — which is exactly the *pemekaran* problem the grid design avoids
everywhere else). Worth raising with the co-authors now rather than in month five: if the
zones are defined as lists of old districts, somebody has to find 1990s district geometry.

---

## 3. Sources recorded in the original `data.md`

Preserved as found, with what is now known about each.

### Agglomeration, built-up, population

**Global Human Settlement Layer** — <https://human-settlement.emergency.copernicus.eu/datasets.php>
Products: degree of urbanisation (SMOD, 1 km), settlement classification, resident population
grid (POP), built-up volume (BUILT-V) and surface (BUILT-S), including a non-residential
component. **All available per 5-year epoch, 1975–2030** — which is the point above.
*Licence: free to use with attribution (European Commission, JRC).*

**WorldPop** — <https://stac.worldpop.org/collections/IDN>
Products: degree of urbanisation (1 km, two grid levels), population per 100 m cell.
A STAC catalogue, so it can be queried programmatically rather than clicked.
*Licence: CC BY 4.0.*
**Where WorldPop and GHS-POP differ, and why it matters here:** WorldPop's "constrained"
products distribute census population only onto cells a built-up layer says are settled;
GHS-POP distributes onto its own built-up surface. Both are *modelled* downscalings of the
same underlying census, so using one as a check on the other mostly checks the downscaling,
not the population. For a pre-period layer, **IPUMS census microdata is the more honest
source** (§5).

### Road networks

**Badan Informasi Geospasial (BIG)** — ArcGIS REST service, *Atlas Transportasi Darat*
<https://geoservices.big.go.id/gis/rest/services/PTRA/Atlas_Transportasi_Darat/MapServer>
**Queried 2026-09-12.** Six layers (ids 1, 3, 5, 7, 9, 11) all report the same 136,810
features: they are the same data rendered at six map scales, not six levels of
generalisation, so layer 1 is as good as any.

**AmeriGeoss / USGEO Indonesia main roads** — <https://data.amerigeoss.org/dataset/indonesia-road-network-main-roads>
Recorded as **unable to download**. Probably not worth chasing: "main roads" only, undated,
and the Geofabrik OSM extract is strictly richer.

### Terrain, water

**BIG** — <https://geoservices.big.go.id/> — terrain, topography, water. **Queried
2026-09-12: water yes, terrain no.** See §4.6 — the geoservices endpoint publishes no
national DEM at all, and BIG's own mapping is derived from SRTM and ASTER anyway.
Mirror where some BIG layers can be downloaded directly:
<https://www.irpanchumaedi.com/post/database/> — **a personal blog, so treat it as a
convenience copy and not as provenance.** For a paper whose central claim is
reproducibility, a layer cited to someone's blog is a weak link: if you use it, record
which BIG product it is a copy of, and the date you took it.

---

## 4. Querying BIG: what the service actually is, and what went wrong

### 4.1 The shape of the thing

`geoservices.big.go.id` runs **ArcGIS Server 10.81** with fifteen folders of services. It
is an API, not a download page. A *MapServer* holds numbered *layers*; a layer's features
come out of its `/query` endpoint, at most `maxRecordCount` per request (1000 on most BIG
layers, 2000 on some).

The folders worth knowing: **`PTRA`** holds the 1:250,000 national atlases (41 services —
transport, rivers, hydrogeology, geology, land cover, hazards, and a set of historical
atlases); **`PKLP`** holds marine and bathymetric data; **`PPIG`** holds the map-sheet
download index. `Utilities` returns `499 Token Required`, so some services are gated.

Everything below was found by enumerating the catalogue rather than guessing layer names:

```
curl -s "https://geoservices.big.go.id/gis/rest/services?f=json"          # folders
curl -s "https://geoservices.big.go.id/gis/rest/services/PTRA?f=json"     # services
curl -s ".../PTRA/Atlas_Transportasi_Darat/MapServer?f=json"             # layers
curl -s ".../MapServer/1?f=json"                                         # fields, limits
```

### 4.2 Use the script, not a hand-written loop

`scripts/fetch_big.py` does the paging. Its header explains the three things a hand-written
loop usually gets wrong, but the short version:

```bash
uv run --script scripts/fetch_big.py \
    --service PTRA/Atlas_Transportasi_Darat --layer 1 \
    --out data/raw/big_atlas_transportasi_darat/2026-09-12/big_transportasi_darat.geojson
```

It asks `returnCountOnly=true` **first**, so there is a denominator to check against; it
sends `orderByFields` so that `resultOffset` means anything at all; and it exits non-zero
rather than writing a partial file. `scripts/check_geojson.py` then checks extent, geometry
types and vertex counts, because a verified feature count says nothing about whether the
geometry is in the right place.

### 4.3 The payload problem, and the one parameter that solves it

The first attempt at the road layer ran for twelve minutes and wrote nothing. The cause was
not rate limiting: **BIG returns 1:250,000 geometry at full vertex density with Z and M
values**, and one page of 1000 river features is **43 MB**. Measured on the same page:

| Request | Size | Time |
|---|---|---|
| baseline (Z+M, 14 decimals) | 43.2 MB | 53 s |
| `returnZ=false&returnM=false` | 43.2 MB | 46 s |
| `+ geometryPrecision=6` | 28.8 MB | 29 s |
| `+ maxAllowableOffset=0.001` | **2.4 MB** | **10 s** |

Two things to take from that table. **`returnZ`/`returnM` are silently ignored** on these
layers — the coordinates still arrive as `[lon, lat, 0.0, null]`, which is half the payload
spent on a zero and a null. And **`maxAllowableOffset` is the whole game**: server-side
Douglas–Peucker simplification, in output-CRS units, 18× smaller.

### 4.4 Why simplifying to ~100 m is not a shortcut

`maxAllowableOffset=0.001` degrees is about 100 m at the equator, and that needs a
justification rather than an apology:

- **At 1:250,000, half a millimetre of map is 125 m on the ground.** A 100 m tolerance
  therefore discards positional precision the source does not actually have. The extra
  vertices are a false claim about accuracy, not information.
- **It is 1% of a 10 km analysis cell** — the unit everything will be aggregated to.
- Douglas–Peucker **preserves endpoints**, so a road network's connectivity survives
  simplification even though its shape is smoothed.

The tolerance and the coordinate precision are written into every output file
(`fetch_max_allowable_offset`, `fetch_geometry_precision`) so that nobody has to guess later
how decimated a layer is. Pass `--max-offset 0` for undecimated geometry and expect roughly
18× the size.

### 4.5 Three failures worth knowing about, because they will recur

**(a) Pagination is not universal.** `PPIG/IDX_Download` rejects `resultOffset` and
`resultRecordCount` outright — `400 Pagination is not supported` — so a fetcher that always
sends them cannot read those layers at all. The script checks
`advancedQueryCapabilities.supportsPagination` first and falls back to a single request
where the layer fits in one, or to walking ranges of the object id where it does not.

**(b) BIG's GeoJSON writer refuses geometries its Esri-JSON writer accepts.** The land
polygon layer failed at `offset 16000` with a bare `400 Failed to execute query`. Bisecting
the object-id range found **exactly one feature**, `OBJECTID 16692`: a polygon off West
Sumatra whose four points all sit on the same meridian — three distinct collinear positions,
`Shape_Area: 0`, about 44 cm long. A zero-area sliver. It is not valid GeoJSON, so the
server's GeoJSON serialiser errors on the whole page; `f=json` returns it happily.

The script now retries a failed page as Esri JSON and converts client-side, so one bad
feature no longer costs the other 999. Degenerate rings are **kept and counted**, not
dropped, so the total still matches the server's — and reported, so you know to run
`make_valid` / `.buffer(0)` before using the layer. *A silently discarded feature is the
thing this whole pipeline is built to prevent.*

**(c) The layers include neighbouring countries.** `check_geojson.py` flagged the coastline
and land layers as extending past Indonesia's northern limit (~5.9°N) to **7.125°N**. Not a
CRS fault: three features named *Garis Pantai Malaka* run up the Malacca Strait into
Malaysia and Thailand, and the land layer's own `NEGARA` attribute gives **17,075 Indonesia,
127 Malaysia, 28 Singapore, 27 Timor-Leste**. For a land mask this is an advantage — Borneo
is shared, and you want its whole outline. For anything claiming to describe Indonesian
territory, filter on `NEGARA`. (The 28 Singapore polygons are incidentally useful: Batam's
adjacency to Singapore is the anchor case in `considerations.md` T4.)

### 4.6 Terrain: BIG is not the source, and does not claim to be

**There is no national DEM on `geoservices.big.go.id`.** The catalogue was enumerated in
full: 41 `PTRA` atlases, 5 `PKLP` marine services, and the rest are thematic or provincial.
The only slope layer anywhere, `DAPIG/LERENG_SEKOLAH`, is a derived school-siting analysis.
Raster services live behind `Utilities`, which requires a token.

Two further findings settle the question rather than leaving it open:

- **The RBI sheet index says what BIG's own mapping is made from.** Field `SBR_DATA2` on
  every 1:250K sheet reads *"ALOS-AVNIR dan Landsat TM5 tahun 2008-2011, **SRTM 30m dan
  ASTER DEM**"*. BIG's terrain is SRTM and ASTER. Using SRTM or Copernicus DEM directly is
  therefore the **upstream** source, not a downgrade from a better national product.
- **Coverage would be partial anyway.** The index has a `DTM` field, and it is a flag, not a
  download link: **62 of 309** sheets at 1:250K have a DTM at all.

**DEMNAS**, BIG's proper national DEM, is published through a separate portal
(<https://tanahair.indonesia.go.id/demnas/>) which returns an empty body to a plain HTTP
request — a JavaScript application requiring a browser and per-tile clicking. If DEMNAS is
wanted later, that is a manual job, and it should be weighed against SRTM/Copernicus being
openly downloadable, globally consistent and already in the Tier A plan.

**Conclusion: take terrain from SRTM or Copernicus DEM GLO-30, as the proposal says.** That
is now a decided question, not an open one.

### 4.7 Licensing — still unresolved, and load-bearing

None of the services carries a licence statement in its metadata. The paper's headline claim
is reproducibility, so "publicly reachable" is not enough: somebody has to establish whether
BIG layers may be redistributed in a replication package. Until then, BIG data is safe to
explore with and not safe to build a published figure on. Tracked as `considerations.md` D4.

**How the repository handles it (2026-10-07).** Every BIG layer is marked `local_only: true`
in `config/map_layers.yaml`, so the committed `map/index.html` contains no BIG geometry; the
full map with BIG layers is written to `outputs/map/index.html`, which is git-ignored. The raw
files are never committed either — `scripts/fetch_big.py` re-fetches them from BIG. **Next
step: ask BIG in writing** (its PPID information office) whether simplified derivatives may be
redistributed with attribution, and file the reply under `metadata/licenses/`. A co-author
writing in Indonesian, from an Indonesian institution, is likely to get the faster answer.

**One grey area to know about:** the terrain overlay on the shared map is masked to land with
BIG's land polygons, so its coastline silhouette derives from BIG. No BIG geometry is in the
page, but if BIG's answer is restrictive, re-mask the terrain from its own data instead.

## 4.8 How to query a BIG ArcGIS REST service — the mechanics

The two BIG entries say "to be queried" and that is a real skill gap, so here is the method.
An ArcGIS **MapServer** is not a file download — it is an API. Open the URL in a browser and
it renders as a readable page listing the service's *layers*, each with a numeric id.

A layer's features come out of its `/query` endpoint:

```
https://geoservices.big.go.id/gis/rest/services/PTRA/Atlas_Transportasi_Darat/MapServer/0/query
  ?where=1%3D1          # "1=1" is true for every row, i.e. give me everything
  &outFields=*          # all attribute columns
  &f=geojson            # GeoJSON out (f=json gives Esri JSON)
  &returnGeometry=true
```

Two things that bite every first time:

- **Servers cap how many features they return** (often 1000 or 2000) and do not always say
  so. The cap is reported as `maxRecordCount` on the layer's own page. Page through with
  `&resultOffset=0`, `1000`, `2000` … and **stop when a page comes back with fewer features
  than the cap, not when one comes back empty** — and record the total, because a silently
  truncated road network produces a market-access surface that is wrong rather than missing.
  The worst failure is the one that looks like success.
- **Coordinate reference system.** Ask for `&outSR=4326` unless you want whatever the
  service's native CRS is. GeoPandas will happily reproject later, but only if the file
  declares a CRS correctly in the first place.

`geopandas.read_file()` will read that query URL directly, which is fine for a look at one
layer. For anything you intend to keep, use `scripts/fetch_big.py` — the difference is that
the script records what it fetched and checks that it got all of it.

---

## 5. Answers to the other questions left in `data.md`

> **"statistics Indonesia for population?"**

Two distinct needs, and BPS answers only one of them.

For the **grid**, BPS is the wrong shape: its published population is by administrative unit,
and the proposal's whole reason for using a grid is to avoid administrative units (§5,
*Unit of analysis*) — both because every Tier A layer is natively raster and because
*pemekaran*, Indonesia's repeated district-splitting, makes an administrative panel require a
boundary crosswalk. Aggregating a grid up to districts to join BPS, then back down, loses
exactly what the grid was for.

For the **pre-period**, the better source is **IPUMS-International**, which holds harmonised
Indonesian census microdata with geography (free, registration only — Tier A in reliability
even though the proposal files it under Tier B). That is what gives you a 1990s labour pool
and migration measure. *Verify which Indonesian census years IPUMS actually carries before
designing around it — the proposal says 1971–2010 and that should be checked against the
catalogue, not assumed.*

BPS remains the right source for two narrower jobs: **validating** the gridded population
against published totals, and the *pemekaran* **crosswalk** if the Tier B merge goes ahead.

> **"add climate data?"**

Not in the current design, and adding it should have to argue its way in. The stack's logic
is *preconditions for industrial agglomeration* (`proposal.md` §4), and the environment
already enters through the layers that bear on whether land is buildable — flood hazard,
surface water, peat, terrain. Rainfall and temperature do not obviously add a precondition on
top of those for manufacturing, as opposed to for agriculture.

Where climate *would* earn a place: if the paper wants to say something about whether the
corridors it recommends are **climate-exposed** — siting new industry on a coast that floods
more each decade. That is a genuine contribution and a different paper's worth of work. Keep
it on the "possible extension" list, not the Tier A list, and note that every layer added to
the stack costs statistical power and adds a way for the model to overfit
— the
familiar overfitting trade-off.

---

## 6. Conventions for this register

- **One row per dataset, written at download time**, with epoch and licence. A row added
  later from memory is a guess.
- **Record the download date and the exact product version** (`R2023A`, `GLO-30`, the
  Geofabrik extract date). GHSL has had several releases and they are not interchangeable.
- **Never edit anything in `data/raw/`.** Processing output goes to `data/interim/` and
  `data/processed/`. If a raw file has to be corrected, the correction is a script, so that
  it is visible and repeatable.
- **Record what a source does *not* contain.** A search that comes up empty should be
  distinguishable from a search that was never run.
