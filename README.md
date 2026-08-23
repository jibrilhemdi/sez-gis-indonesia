# Predicting Where Agglomeration Takes Root

**An open-data suitability model for industrial location in Indonesia**

Converting a retrospective policy failure into a prospective spatial instrument — built entirely on open, secondary data.

---

## Status

**Early setup.** The research proposal is complete; the pipeline is not yet implemented. This repository currently holds the proposal and project scaffolding. See [Roadmap](#roadmap) for what is planned and in what order.

| | |
|---|---|
| **Stage** | Proposal complete, implementation not started |
| **Proposal** | Full research proposal (July 2026) — circulated separately, not tracked in this repo |
| **Timeline** | 9–12 months to first submission |
| **Data** | 100% open / secondary — no primary collection, no human-subjects approval on the critical path |

---

## The problem

Manufacturing clusters rather than spreading evenly, because agglomeration economies — a shared labour pool, a dense supplier web, knowledge spillovers — are self-reinforcing. That same self-reinforcement creates a coordination failure: no firm wants to be first into a location with no suppliers and no trained workforce, so a site can stay empty even when its fundamentals would support a cluster.

Governments try to substitute fiscal incentives for missing fundamentals. Indonesia ran this experiment at scale with **KAPET** (*Kawasan Pengembangan Ekonomi Terpadu*, Integrated Economic Development Zones), granting capital and labour tax breaks to firms locating in selected Outer Island districts from the late 1990s. The most rigorous evaluation (Rothenberg et al.) finds it did not work: no measurable gains in firm entry, output, migration, or welfare.

The lesson is not that incentives never matter, but that **they are a tiebreaker between otherwise-viable sites, not a foundation**. Which makes the binding question spatial: *where do the fundamentals already exist, or come cheapest to complete?*

## The research gap

Three literatures bear on this, and the gap sits precisely between them:

- **Place-based policy evaluation** is rigorous but *retrospective* — it tells us badly sited zones fail, not where the next zone should go.
- **GIS multi-criteria suitability analysis** is prospective but uses *asserted* weights (AHP, weighted overlay) that are never validated against realized outcomes.
- **Quantitative economic geography** has the theory and identification tools, but is rarely operationalized as a wall-to-wall, reproducible, open-data surface a planner could read off a map.

This project is the synthesis: an empirically estimated, outcome-validated, fully reproducible suitability model that (i) replaces asserted weights with weights learned from Indonesia's own history of cluster success and failure, (ii) validates them against a genuine natural experiment, and (iii) uses the model's *residuals* to locate latent potential rather than merely ranking sites.

---

## Research questions

**RQ1 — Measurement.** Can the theoretical preconditions for self-sustaining industrial agglomeration be operationalized as a stack of spatial surfaces at grid resolution across Indonesia using only open geospatial data?

**RQ2 — Validation.** Which precondition layers, and in what configuration, historically discriminated between grid cells where industrial activity became self-sustaining and those where it stagnated — and does that configuration explain the observed failure of the KAPET zones?

**RQ3 — Latent potential.** Where is the gap between predicted suitability and realized agglomeration largest, and which single precondition is the binding constraint at each such location?

The staging is deliberate: **RQ1–RQ2 are the secure core and depend only on guaranteed open data.** RQ3 extends them without introducing fragile dependencies.

---

## Conceptual framework

The framework rests on a distinction most suitability studies collapse: **suitability is not realization.** Fundamentals determine whether a cluster *could* take root; whether one *has* depends additionally on history, coordination, and the arrival of an anchor. The wedge between the two is the object of interest.

The preconditions form a stack, ordered by how load-bearing they are:

| Layer | Role | Why it matters |
|---|---|---|
| Market access | Foundation | Reach to ports and population over the real network; without it output cannot move to demand |
| Reliable power | Non-negotiable | Factories do not operate on intermittent supply |
| Port & logistics | The archipelago's weak point | In an island economy, port access dominates tradable-goods viability |
| Labour pool | Enabling | Sufficient workers at a competitive wage |
| Land, water & housing | Enabling | Developable, non-hazardous land where a workforce can live |
| Fiscal incentives | **Tiebreaker only** | Effective only once the layers beneath are present — the KAPET lesson |

Two elements sit outside the stack. The **anchor** (a lead firm, or proximity to an existing hub such as Batam's adjacency to Singapore) is a discrete event, not a continuous surface, and enters as a covariate. **Fiscal incentives** are modelled as the policy *treatment*, not a suitability input — the entire point is to test whether they can compensate for a weak stack.

This yields the empirical prediction that structures the analysis: *realized agglomeration should be a function of the fundamental stack; the residual marks latent potential; and KAPET designation should carry little explanatory power once the stack is controlled for.*

---

## Method

Three tiers of ambition, mirroring the research questions.

### Tier 1 — Rule-based suitability baseline
A conventional weighted-overlay surface, to give the estimated model something to beat. Weights come from equal weighting and from published studies — **no expert elicitation, interviews, or surveys**. Using asserted weights here is the point, not a shortcut: the only methodological difference from Tier 2 is *where the weights come from*, so an elicitation-free baseline cleanly isolates the contribution.

### Tier 2 — Empirically estimated viability model (the core)

- **Panel construction.** Per-cell agglomeration trajectories from harmonized night lights (and GHSL built-up as a robustness alternative), 1992–2020. *Self-sustaining* is operationalized as sustained above-trend growth persisting over a multi-year window after emergence — not a transient spike. Multiple thresholds and both proxies carried through as sensitivity analyses.
- **Pre-period predictors.** Fundamentals measured circa 1992–2000, before most designations and cluster maturation, to break reverse causality (successful clusters have good infrastructure *because* they succeeded).
- **Two complementary estimations.** Gradient-boosted trees / random forests under **spatial block cross-validation** (yielding the wall-to-wall surface plus partial-dependence and Shapley decompositions), alongside a spatial panel — Durbin / lag / error specification — for interpretable marginal effects. The ML surface is the prescriptive product; the econometrics is the referee-defensible core.
- **Natural-geography instruments.** Market and port access instrumented with time-invariant exogenous geography: natural-harbour suitability (bathymetry + coastline geometry), terrain ruggedness, coastal distance. Open-data by construction.
- **KAPET validation — the decisive test.** KAPET designation entered as a treatment indicator. We expect (i) KAPET cells to sit low in the predicted-suitability distribution, (ii) their realized trajectories to track their low predictions, and (iii) the KAPET dummy *not* to improve fit once fundamentals are included. A model that explains the KAPET failure this way is externally validated against a real policy experiment — the credibility anchor of the paper.

### Tier 3 — Residual analysis and binding constraint
The residual surface (predicted suitability minus realized agglomeration) is the prescriptive product. High positive residuals mark cells whose fundamentals exceed their realized activity — latent potential held back by coordination failure or a single missing layer. Partial-dependence structure then names the **binding constraint** at each. Illustrative corridors include Makassar, Medan–Kuala Tanjung, and Batam–Bintan expansion.

> **Note on scope.** An earlier framing posed the prescriptive step as *minimum-viable-bundle* optimization — the cheapest marginal infrastructure addition that flips a site above threshold. That needs credible infrastructure unit costs, which are not openly available for Indonesia and would make the headline result hostage to the weakest data in the pipeline. The residual-and-binding-constraint reframing recovers most of the policy insight using only Tier A data. A deliberate trade of a fragile deliverable for a robust one.

---

## Data

Data availability is the primary risk to this class of project, so the design uses a **three-tier reliability structure**. The load-bearing analysis depends only on Tier A.

### Tier A — Open, downloadable, natively gridded (the core)

| Layer | Dataset | Coverage / resolution |
|---|---|---|
| Agglomeration & outcome | Harmonized DMSP-OLS + VIIRS night lights (Li et al. 2020) | 1992–present, ~1 km |
| Built-up / population | GHSL; WorldPop | GHSL from 1975; ~100 m–1 km |
| Road network | OpenStreetMap (Geofabrik Indonesia extract) | Current; vector |
| Terrain | SRTM / Copernicus DEM | 30 m |
| Flood & water | JRC Global Surface Water; global flood hazard | ~30 m–1 km |
| Peatland | Global / Indonesian peatland maps | National; raster |
| Port activity | IMF PortWatch (satellite-AIS-derived) | Daily 2019–present; 2,065 ports |
| Ports (historical) | Static gazetteers; PortWatch points | Time-invariant |
| Coast & bathymetry | OSM coastline; GEBCO | Global |
| Policy treatment | KAPET boundaries; current SEZ registry (~25 zones) | National; vector |

### Tier B — Bureaucratic but reliable (enhancement, never a dependency)

| Layer | Dataset | Access route |
|---|---|---|
| Plant-level manufacturing | Survei Industri Besar dan Sedang (IBS) | BPS Silastik: abstract + SPPD + fee |
| Labour & wages | Sakernas | BPS Silastik |
| Census / demographics | IPUMS-International (1971–2010) | Free, registration only |

The Silastik route is *friction, not a wall*, and is much easier with an Indonesian institutional affiliation. IPUMS is effectively Tier A in reliability and backstops the pre-period labour and migration layers. **Silastik acquisition runs on its own track from month 1 precisely because its timeline is least predictable — the core paper does not wait on it.**

### Tier C — Genuinely uncertain (future work only)
Grid-level electricity reliability (PLN SAIDI/SAIFI), full Satu Peta consolidation, geocoded firm/investment registries. **No research question depends on these.**

### Unit of analysis

A **regular grid** — 10 km baseline, with 5 km and 25 km for sensitivity. Three reasons: every Tier A layer is natively raster, so a grid avoids lossy aggregation; it dissolves the small-*N* problem (thousands of cells rather than ~25 zones); and it sidesteps *pemekaran*, Indonesia's repeated district-splitting, which would otherwise demand a boundary crosswalk for any panel. Administrative units are used only as the join key for Tier B tabular merges.

---

## Threats to validity

Each threat has a mitigation built into the design, and every mitigation for the core is executable on Tier A data.

| Threat | Mitigation |
|---|---|
| Reverse causality | Pre-period predictors (1992–2000); natural-geography instruments |
| Small *N* of zones | Grid-level outcome; zones become a treatment subsample, not the sample |
| "Self-sustaining" is unobserved | Multi-year persistence; sensitivity across thresholds and two proxies |
| Night-lights blooming / error | GHSL built-up as alternative proxy; standard corrections; report both |
| MAUP | Run at 5 / 10 / 25 km; report resolution sensitivity |
| Spatial autocorrelation | Spatial block CV; spatial lag/error models; Moran's I on residuals |
| Boundary changes (*pemekaran*) | Grid-primary design; crosswalk only for the Tier B merge subset |
| PortWatch starts ~2019 | Contemporary throughput only; static port locations for the pre-period |
| Sectoral aggregation | Sector-agnostic core; sectoral split as a Tier B extension |

**The design's defining property: no single data failure reaches the core result.** The worst realistic case — losing all of Tier B and Tier C — costs the paper its sectoral extension and energy-reliability precision, leaving RQ1, RQ2, the KAPET validation, and RQ3 intact.

---

## Roadmap

| Phase | Months | Focus | Blocks on |
|---|---|---|---|
| 1. Data assembly & pipeline | 1–3 | Tier A raster stack; grid at three resolutions; access surfaces | None (open data) |
| 2. Baseline suitability | 2–3 | Tier 1 rule-based benchmark | Overlaps Phase 1 |
| 3. Viability model & KAPET validation | 3–7 | Tier 2 ML + spatial econometrics; instruments; the KAPET test | Phase 1 |
| 4. Residual & corridor analysis | 6–9 | Tier 3 residual map, binding constraints, corridors | Phase 3 |
| 5. *(Optional)* Tier B extension | parallel | Silastik/IPUMS; sectoral heterogeneity | Silastik processing |
| 6. Writing & submission | 8–12 | Draft, internal review, framing, submission | Phases 3–4 |

---

## Repository layout

> **Planned.** Only the proposal, `README.md`, and `.gitignore` exist so far. This section is the target structure, not a description of what is here.

```
.
├── data/
│   ├── raw/          # downloaded as-is, never edited        (git-ignored)
│   ├── interim/      # intermediate processing               (git-ignored)
│   ├── processed/    # analysis-ready raster stack           (git-ignored)
│   └── external/     # third-party reference layers          (git-ignored)
├── src/              # reusable pipeline modules
├── notebooks/        # Marimo notebooks (plain .py — tracked)
├── scripts/          # data acquisition + build entry points
├── figures/          # generated maps and plots              (git-ignored)
└── outputs/          # model results, surfaces               (git-ignored)
```

**Data is not in the repository.** GIS files are large binaries; GitHub rejects anything over 100 MB and a committed large file stays in history even after deletion. The repo carries *the script that fetches or builds the data*, not the data itself — which is also what makes the pipeline reproducible rather than merely archived. To commit a small reference file anyway: `git add -f path/to/file`.

## Getting started

> Not yet applicable — no pipeline code exists. Once Phase 1 lands, the intended workflow is:

```bash
git clone https://github.com/jibrilhemdi/sez-gis-indonesia.git
cd sez-gis-indonesia
uv sync                      # reproduces the environment from uv.lock
uv run scripts/fetch_data.py # download Tier A layers into data/raw/
uv run scripts/01_prepare.py # build the raster stack
```

Python, managed with [uv](https://docs.astral.sh/uv/). `uv.lock` is committed deliberately — it pins exact versions so the environment rebuilds identically on another machine.

---

## Contributions

**Methodological.** Reframes retrospective place-based-policy evaluation as a prospective, reproducible spatial instrument: estimated rather than asserted weights, validated against a natural experiment, with residual-as-latent-potential and binding-constraint decomposition replacing cost-dependent bundle optimization.

**Empirical.** The first fully open-data, sub-national viability surface for Indonesian industrial location, externally validated on KAPET, with an accompanying map of under-built high-potential corridors.

**Transfer.** Because the core runs entirely on open data, the method is directly portable to other archipelagic and lower-middle-income economies facing the same question.

## Target venues

In order of fit — the same analysis supports all of them; only the framing shifts.

1. *Computers, Environment and Urban Systems* — reproducible spatial method + planning application
2. *Applied Geography* — applied spatial analysis with a clear policy problem
3. *Papers in Regional Science* / *Journal of Regional Science* — if identification is foregrounded
4. *Habitat International* or a development journal — if the Indonesia policy angle leads

## Key references

- Rothenberg, Wang & Chari (2025). When regional policies fail: an evaluation of Indonesia's Integrated Economic Development Zones. *Journal of Development Economics.* — **the KAPET evaluation this project inverts**
- Li, Zhou, Zhao & Zhao (2020). A harmonized global nighttime light dataset 1992–2018. *Scientific Data* 7.
- Donaldson & Hornbeck (2016). Railroads and American economic growth: a "market access" approach. *QJE* 131(2).
- Redding & Rossi-Hansberg (2017). Quantitative spatial economics. *Annual Review of Economics* 9.
- Neumark & Simpson (2015). Place-based policies. *Handbook of Regional and Urban Economics* 5.
- Kline & Moretti (2014). Local economic development, agglomeration economies, and the big push. *QJE* 129(1).
- Henderson, Storeygard & Weil (2012). Measuring economic growth from outer space. *AER* 102(2).
- IMF PortWatch. Daily port activity data and trade estimates.

Full bibliography in the research proposal (circulated separately).

---

## Attribution

Analysis derived from OpenStreetMap data requires attribution: **© OpenStreetMap contributors**, ODbL.

## License

*To be decided.* Given the reproducibility aim, an open licence is expected — code under MIT or BSD-3, and any derived data products under CC BY 4.0.
