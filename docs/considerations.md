# Considerations

**A standing register of the methodological and theoretical decisions this paper has to
defend.** Not a to-do list and not a criticism of the proposal — a list of the places where a
choice has been made, or still has to be, and where a referee will press.

## How to read this file

Each entry says **what the issue is**, **why it bites**, and **what to do**. Each carries a
status:

| | |
|---|---|
| **Open** | Needs a decision, or an answer from the co-authors |
| **Decided** | Settled, recorded with the reason, so it is not re-argued |
| **Watch** | No action yet; becomes live at a specific later stage |

**Why keep this separately from the proposal.** A proposal argues *for* a design — it is
written to persuade, so its weak points are the parts written most smoothly. This file is
written to find them. Keeping the two apart means the proposal can stay a clean argument while
the doubts stay recorded instead of being quietly forgotten, and it means that when a referee
raises something, the answer already exists in writing.

Entries are prefixed by type: **T** theory, **M** measurement, **I** identification and
inference, **S** spatial method, **D** data, **F** framing.

---

# Part I — Theory

## T1. "Suitability is not realisation" is a theoretical commitment, not a neutral distinction

**Status: Decided, but state it explicitly in the paper.**

The framework's central move is to separate *fundamentals* (could a cluster form here?) from
*realisation* (did one?), and to read the wedge between them as latent potential. That requires
fundamentals to be **prior to and separable from** the history of agglomeration.

**Agglomeration theory says they are not.** Roads get built where industry already is. Ports
are deepened where volume already exists. The labour pool is trained because employers came.
Every layer in the precondition stack is partly *endogenous* to past agglomeration — which is
the same fact as the reverse-causality problem, seen from the theory side rather than the
estimation side.

This is not a fatal objection, because the design already answers it twice: **pre-period
measurement** and **natural-geography instruments**. But it changes what those devices are
doing. They are not robustness checks bolted onto a clean framework; they are **what makes the
framework coherent at all**. Write them that way. A reader who understands that the separation
is earned rather than assumed will trust the rest; one who thinks the paper simply assumes
fundamentals are exogenous will not.

## T2. Mapping each layer to a Marshallian mechanism is the contribution, so make it explicit

**Status: Open — write the table into the paper.**

The suitability literature the paper criticises assembles layers *because they are available*.
The difference here is supposed to be that the layers are theoretically motivated. That
difference only exists on the page if the mapping is printed:

| Micro-foundation | What it is | Layer that proxies it |
|---|---|---|
| **Sharing** | Indivisible infrastructure and suppliers spread over more users | Power reliability; port and logistics |
| **Matching** | Thicker labour markets, better firm–worker matches | Labour pool accessibility |
| **Learning** | Knowledge spills over between nearby people | Existing agglomeration; proximity to an anchor |

Source: Koster (2024), *Understanding Spatial Agglomeration* (Annual Review) — Marshall's
three, formalised by Duranton and Puga.

**Where this gets uncomfortable, and should be admitted rather than smoothed over.** The
mapping is not one-to-one. Port access proxies sharing *and* transport cost. Existing
agglomeration proxies learning *and* is a lagged version of the outcome. A layer that proxies
two mechanisms cannot tell you which one is binding — which matters, because naming the binding
constraint is RQ3's whole deliverable. Say which mappings are clean and which are not.

## T3. Agglomeration diseconomies are absent from the stack

**Status: Decided — defensible, but say so in one sentence.**

Land rent, congestion, pollution and the housing costs that eat the wage premium are the
centrifugal half of the mechanism (`us730e-synthesis.md`), and the stack has no layer for them.
Defensible: Indonesia's Outer Islands, where KAPET sat and where the latent-potential corridors
are expected, are nowhere near the congestion frontier.

**But it limits what the surface can say about Java**, which *is* near that frontier and which
will contain many of the highest predicted-suitability cells. A model with no diseconomies term
will predict that the best place for new industry is the place that already has the most — and
it will be right about fundamentals and useless as advice. Either exclude Java's core from the
prescriptive claims, or include a congestion/land-cost proxy, and say which and why.

## T4. The anchor problem: a suitability surface predicts where a cluster would succeed, not where one will appear

**Status: Watch — becomes live when RQ3's recommendations are written.**

The proposal treats the anchor (a lead firm, or adjacency to an existing hub like Batam to
Singapore) as a discrete event and therefore a covariate rather than a surface. That is the
right modelling call. The theoretical consequence is under-stated: if anchors are what actually
*start* clusters, then a high-residual cell is a place where an anchor would thrive, not a place
where one is coming.

That is still a useful thing to tell a planner — it is the difference between "invest here" and
"this is where to aim an anchor-attraction effort". But the two are different
recommendations, and the paper should make the claim it can support. Compare
Park (2002) on Swedish science parks and Nauwelaers et al. (2013) on the Øresund
region: state attempts to
manufacture agglomeration in a high-income setting, where the anchor had to be recruited.

## T5. The tiebreaker claim implies an interaction, not a main effect — and the test should match

**Status: Open. This is the single highest-value item in this file.**

The paper's theoretical position is that fiscal incentives are **a tiebreaker between
otherwise-viable sites, not a foundation**. Read that carefully: it says the effect of an
incentive *depends on the level of fundamentals*. That is an **interaction effect**, and the proposal's stated test is a **main effect** — does
adding a KAPET dummy improve fit.

The two are not the same hypothesis, and the mismatch matters in both directions:

- A KAPET dummy can be indistinguishable from zero *on average* while incentives work perfectly
  well in the handful of designated cells that did have decent fundamentals. The proposal's test
  would report "incentives don't work" and the theory's own claim would be the reason it is
  wrong.
- The interaction has a far more interesting finding available to it. If `KAPET × suitability`
  is positive, the paper can say: **incentives work, but only where they are least needed** —
  which is a sharper and more policy-relevant result than another null, and it is the direct
  prospective counterpart to Rothenberg et al.'s retrospective one.

**Do this:** keep the dummy (it answers the proposal's stated question and the literature
expects it), and add the interaction with predicted suitability. Report both, and read the interaction coefficient as
conditional on the level of suitability, not as a standalone effect.

## T6. The same result supports two incompatible readings, and that is worth owning

**Status: Watch — a discussion-section decision, and a framing choice.**

"Zones fail where fundamentals are absent" is compatible with:

- **the economist's reading** — the siting was bad, and better siting would work; and
- **the critical-geography reading** — zone policy redistributes activity toward places that
  already have advantages, which is exactly what uneven development predicts
  (Harvey 2005, *A Brief History of Neoliberalism*; Das 2017 on Harvey's theory of uneven
  development).

The difference is not empirical. It is what the result is taken to be evidence *for*. The
paper's prescriptive framing assumes the first, and a development or geography reviewer will
supply the second.

**The honest move, and the one that makes the paper better:** say that the model identifies
where industry can take root *given the existing distribution of advantage*, and that this is a
description of the constraint, not an endorsement of concentrating investment where advantage
already sits. The equity question — whether a state should put industry where it is cheapest or
where people are poorest — is a real question the model does not answer, and naming it is
stronger than letting a reviewer name it first.

---

# Part II — Measurement and operationalisation

## M1. The outcome definition is the paper's most exposed choice

**Status: Decided in principle (sensitivity analyses), Open in detail.**

*Self-sustaining* is unobserved. It is operationalised as sustained above-trend growth
persisting over a multi-year window after emergence. Every word there is a free parameter:
above *which* trend, how far above, how many years, and what counts as emergence.

The proposal's answer — multiple thresholds and both proxies carried through — is right. The
thing to add is that the parameter grid should be **chosen and written down before the results
are seen**, because otherwise the sensitivity analysis becomes a menu — the
"researcher degrees of freedom" problem. Pre-registering it internally, even informally
in this repo with a dated commit, is cheap and converts "we checked robustness" into something
verifiable.

## M2. Night lights measure electrified activity, not industry

**Status: Open — needs to be stated, and ideally tested.**

There is a standing critique of remotely sensed development measures in the
machine-learning-for-development literature: **they predict *the survey*, not the thing**, and because the
predictors are physical they can encode a historically contingent visual signature of
development and then apply it where development looks different — **spatial
non-transferability**, a geographer's objection the ML literature under-makes.

Applied here, specifically: a mine or a refinery lights up brilliantly; a labour-intensive
textile or food-processing cluster may barely register. In a resource-extraction economy that
is not noise, it is **bias in a known direction** — the outcome variable is partly a measure of
capital- and energy-intensity rather than of agglomeration.

**That this bias has a direction is good news.** It makes a prediction: if lights are biased
toward extraction, then model-vs-built-up disagreement should be largest in mining regions.
Testable, cheaply, with data already in the plan. A stated and tested bias is a contribution;
an unstated one is what a referee finds.

## M3. The harmonised night-lights product is itself a model

**Status: Open — one paragraph in the data section.**

DMSP-OLS and VIIRS are different sensors with different radiometry. The Li et al. (2020)
harmonised series is *fitted*, not measured: the inter-sensor calibration is a statistical
model. So the outcome variable carries a model's error, and that error is not independent of
time — it is largest around the 2012–13 sensor transition, which sits inside the study window.

**Consequence to check:** an apparent change in trajectory around 2012–13 may be the sensor,
not the economy. Anything in the results that hinges on a break near that date needs the
built-up proxy to agree before it is believed.

## M4. DMSP saturation and blooming, and why an archipelago makes blooming worse

**Status: Open — standard corrections are named in the proposal; the archipelago angle is not.**

Two known DMSP defects, each interacting badly with this specific design:

- **Saturation.** DMSP digital numbers are top-coded at 63. A cell already at the ceiling
  **cannot exhibit above-trend growth**, so the brightest cells are mechanically excluded from
  qualifying as "became self-sustaining". If the outcome is a growth measure, the already-dense
  core of Java is censored, and the model learns from the cells where growth is *visible* rather
  than where it happened.
- **Blooming.** Light spills beyond its source, and it spills especially far over **water**,
  which reflects. For a 17,000-island study area with a 10 km grid, blooming systematically
  brightens coastal and small-island cells — and coastal cells are exactly where ports,
  market access and the paper's candidate corridors are. The measurement error is **correlated
  with the key predictor**, which is the one kind of measurement error that biases coefficients
  rather than just adding noise.

**Do this:** apply the standard saturation correction and report how many cells are censored;
build the land mask first (see S3) and report blooming sensitivity by distance to coast.

## M5. Pre-period predictors and the outcome come from the same series — check the windows do not overlap

**Status: Open — a specification detail with a mechanical consequence. A question for the
co-authors.**

*Added 2026-10-07:* the GHSL robustness series moves in 5-year steps (1990, 1995, 2000, …,
2020), so the proposal's "circa 1992–2000" has to become a choice of epochs — e.g. predictors
from 1990 + 1995 with the outcome from 2000, or predictors from 1990–2000 with the outcome from
2005. The two give different panels, and the night-lights outcome (annual from 1992) should use
the same cut so the two proxies are comparable.

"Existing agglomeration" is a pre-period predictor measured from night lights circa 1992–2000.
The outcome is a night-lights growth trajectory over 1992–2020. **If those windows overlap, part
of the correlation is arithmetic**: a cell's 1992–2000 brightness appears on both sides of the
equation, and a series is correlated with its own growth through the shared starting level.

The fix is simple and needs to be deliberate: predictors from a strictly earlier, non-overlapping
window than the outcome (e.g. predictors 1992–1996, outcome growth from 1997), and say so. The
cost is a shorter outcome panel. This is the kind of thing that is invisible in a results table
and obvious to a referee who has built a similar panel.

## M6. The transfer claim is asserted, and could be tested almost for free

**Status: Open — a cheap, high-value addition.**

The paper claims the method is "directly portable to other archipelagic and lower-middle-income
economies". Nothing in the design tests that.

It could, at almost no cost, with the data already in hand: **fit on one region of Indonesia and
predict another** — Sumatra to Sulawesi, say, or Java to the Outer Islands. That is spatial
extrapolation rather than spatial interpolation, and it is precisely the
**non-transferability** critique in M2 turned on the paper's own model. If performance holds,
the transfer claim has evidence. If it collapses, that is a *finding* — and a more honest one
than an untested assertion. Either way it costs one extra cross-validation scheme.

## M7. The road hierarchy is real but thin, and 59% of the network has no class

**Status: Open — affects how market access is computed.**

Market access needs a network with travel *speeds*, and speeds normally come from a road
class. BIG's layer does carry the Indonesian statutory hierarchy in `NAMA_UNSUR`, which is
better than expected. The problem is the distribution. Measured on the downloaded layer
(lengths computed after simplification, equirectangular approximation):

| Class | Features | km | % of km |
|---|---|---|---|
| *Jalan Lain* — "other" | 99,518 | 282,459 | **59.4%** |
| *Jalan Lokal* — local | 18,567 | 75,028 | 15.8% |
| *Jalan Kolektor* — collector | 3,604 | 66,164 | 13.9% |
| *Jalan Setapak* — footpath | 14,395 | 36,273 | 7.6% |
| *Jalan Arteri* — arterial | 233 | 8,622 | 1.8% |
| *Jalan Tol* — toll, dual carriageway | 103 | 614 | 0.1% |
| *Jalan Lori* — tramway/trolley road | 106 | 700 | 0.1% |

**Only about 32% of network length carries a class that maps to a speed.** Nearly 60% is
"other", which could be anything from a district road to a plantation track, and a further
7.6% is explicitly footpath — not traversable by a truck at all.

Assigning one speed to *Jalan Lain* is a decision that silently sets most of the country's
market-access surface, and its direction of error is not neutral: guess high and remote
districts look better connected than they are, which **inflates suitability exactly where the
KAPET zones were** and weakens the paper's central test. Guess low and Java's dense local
network is under-weighted.

**Do this:** treat the *Jalan Lain* speed as a sensitivity parameter rather than a constant,
report the surface under a low and a high assumption, and check whether the KAPET result
survives both. Cross-checking against OSM's `highway=` tags on a sample is the cheap way to
learn what *Jalan Lain* actually contains.

## M8. The "road" layer contains railways and airport runways

**Status: Decided — filter it, and the filter is a one-liner. Recorded because it is silent.**

`Atlas_Transportasi_Darat` is a *land transport* atlas, not a road atlas. Of its 136,810
features, **195 are railway** (*Jalan Kereta Api*, single and double track) and **89 are
airport runways** (*Landas Pacu*, four classes) — 5,988 km in total.

Loaded without filtering, a routing graph will happily send freight along a runway and
across a railway, and nothing will complain. It is a small share of length (1.3%) and a
serious share of nonsense, because runways sit *at* airports, i.e. adjacent to exactly the
urban cells whose accessibility is being measured.

Worth noting as a validation success too: the 5,988 km of rail in this layer matches
Indonesia's actual rail network of roughly 6,000 km, which is independent evidence that the
download is complete and the lengths are being computed correctly.

## M9. Server-side geometry simplification is a measurement decision, so it is recorded

**Status: Decided.**

Every BIG layer was fetched with `maxAllowableOffset=0.001` (~100 m) because the
unsimplified payload is 18× larger and the road layer could not be downloaded at all without
it. That is a convenience motive, but the decision is defensible on its own terms: **at
1:250,000 a half-millimetre of map is 125 m on the ground**, so a 100 m tolerance discards
precision the source never had, and it is 1% of a 10 km analysis cell. Douglas–Peucker
preserves endpoints, so network connectivity survives.

The reason it belongs in this file rather than only in the data register: simplification
changes computed **lengths**, and lengths become travel times, and travel times become market
access. The effect here is far below the noise floor of the class-speed problem in M7 — but
it is a choice that was made, it is recorded in each output file
(`fetch_max_allowable_offset`), and it can be undone with `--max-offset 0` if a referee asks.

---

# Part III — Identification and inference

## I1. The KAPET test argues from a null, so report intervals rather than p-values

**Status: Open — affects how results are written up.**

Prediction (iii) of the validation is that the KAPET dummy does **not** improve fit once
fundamentals are included. The test succeeds by a coefficient being indistinguishable from zero.

**An argument from a null is only as strong as its precision.** A wide interval around zero is
equally consistent with "no effect" and "an effect we cannot detect", and a non-significant
result with low power is not evidence of absence. So the claim must be that the estimate is
*precise and near zero*, not merely insignificant: report the confidence interval and, ideally,
state in advance the effect size the design can detect.

## I2. A null from a measure that may not see the treated activity

**Status: Open — the specific vulnerability of I1 in this paper.**

Rothenberg et al. find the KAPET null using **firm-level data** — entry, output, employment.
This paper would find a KAPET null using **night lights**. Those are not the same finding, and
a referee who knows the evaluation will spot the gap immediately:

> If lights do not detect the kind of activity KAPET subsidised (small, labour-intensive,
> low-energy manufacturing — see M2), then a null in lights is partly a null in the instrument.

This does not break the validation, because agreement with a firm-level study using an
independent measure is *stronger* evidence than either alone. But it has to be argued that way —
"two different measures agree" — rather than presented as independent confirmation without
noticing that one of the two measures might be blind to the treatment. The built-up proxy and,
if Tier B lands, the IBS plant-level data are what turn this from a weakness into a triangulation.

## I3. The instruments' exclusion restriction is the weakest link, and it is attackable

**Status: Open — needs an argued defence, not a citation.**

Market and port access are instrumented with time-invariant geography: natural-harbour
suitability, terrain ruggedness, coastal distance. Relevance is not in doubt. **Exclusion is.**

Ruggedness plausibly affects industrial outcomes through channels that have nothing to do with
market access: agricultural productivity, historical settlement patterns, conflict and state
reach, malaria ecology. Coastal distance likewise — coasts differ in trade history, colonial
administration and population, not only in transport cost. A development economist will raise
exactly this, because it is the standard objection to geography-as-instrument.

**Do this:** defend each instrument separately rather than as a set; name the alternative
channels and show what happens when the obvious ones are controlled for directly; and report
the reduced form, because a reader who doubts the exclusion restriction still learns something
from the instrument's raw association with the outcome.

## I4. Pre-period roads do not exist in OpenStreetMap — and BIG does not solve it either

**Status: Open — a question for the co-authors. Narrowed 2026-09-12.**

The Tier A table lists the road network as "current". The method requires market access
measured circa 1992–2000. OSM cannot supply a 1990s network.

**BIG was the obvious hope and it is not an answer.** The RBI 1:250,000 network was
downloaded on 2026-09-12, and every one of the 309 index sheets reports `THN_BUAT` = **2013**,
from source imagery of 2008–2011. So BIG gives a second *contemporary* network, not a
historical one. That is still worth having — see M7 on what it is good for — but the
pre-period gap is unchanged and now demonstrably not closable from either open source.

Three ways out, and they are not equally good: (a) the natural-geography instruments carry
identification on their own — a stronger claim than the proposal currently makes, and it should
be made deliberately if it is the plan; (b) find a historical network (digitised maps, or an
older GIS dataset); (c) restrict the road-based layers to a contemporary specification and be
explicit that those layers are not pre-period. **Raise this before Phase 1 ends**, because the
answer changes what gets built.

## I5. Whether the residual is signal or error is the hinge of RQ3

**Status: Open. Second most important item in this file.**

Tier 3 reads a high positive residual as **latent potential**. A residual is also, by
definition, **the model being wrong at that cell**. Those two readings are indistinguishable
from the residual alone.

What separates them is the *structure* of the error. If residuals are small and spatially
unstructured, a large one is plausibly substantive. If residuals are spatially clustered, then
high-residual regions are where the model is systematically wrong — missing a variable, wrong
functional form — and reading them as latent potential is reading the model's ignorance as a
policy recommendation.

**So Moran's I on residuals is not a robustness check in this paper — it is a precondition for
RQ3 to mean anything**. Run it, report it, and say
plainly what it licenses. If residuals *are* clustered, that is still interesting; it just means
the honest product is "here is what the stack does not explain", which is a different and more
modest claim than "here is where to invest".

## I6. Binding constraint is a cell-level claim that will be read as a site-level recommendation

**Status: Watch — a writing-up discipline.**

Partial dependence names which layer is limiting *for a grid cell*. Policy acts on sites and
firms. A 10 km cell can easily contain a viable site and an unbuildable swamp, and the cell's
binding constraint is neither site's — the ecological fallacy, in planning form. The claim the analysis supports is "at this resolution, this
layer limits this area" — and the gap between that and "build a road here" is where a planner
will misread the map. Say what a cell is.

---

# Part IV — Spatial method

## S1. Random cross-validation folds leak, and the leak flatters the model

**Status: Decided — spatial block CV is in the design. The detail below is not.**

Nearby cells resemble each other, so a random fold puts a cell's neighbour in the training set
and most of the answer with it. The model scores well and generalises nowhere. Blocking folds
geographically is the fix, and it is the spatial version of the clustering problem econometrics solves
with clustered standard errors, and of the independence assumption spatial statistics tests
with Moran's I. **Same fact about the world, three vocabularies** — which is worth knowing because
the literature will describe it in whichever one its discipline uses.

## S2. Block size is a researcher degree of freedom and should be estimated, not chosen

**Status: Open.**

Spatial block CV only works if a block is **larger than the range of spatial autocorrelation**
in the data. Too small and the leak persists; too large and there is too little training data
and the score becomes pessimistic. Picking a round number is a free parameter nobody will
notice.

**Do this:** estimate the autocorrelation range from a variogram or Moran correlogram on the
outcome, set the block size from it, and report both the estimate and the sensitivity. That
turns an arbitrary choice into a measured one, and it is a paragraph most papers do not bother
to write.

## S3. The land mask comes first, or the spatial weights matrix is fiction

**Status: Open — must precede grid construction.**

A known failure from coastal regionalisation work: administrative polygons often run to the
maritime border, so unclipped units overstate land area — in one Swedish case by more than
half — and, the part that actually matters, **the contiguity graph makes units neighbours
through open water**, so any spatial model runs on a partly fictitious adjacency graph.

Every one of those failures is larger here. A 10 km grid over Indonesia is mostly sea. Without
a land mask the spatial weights matrix treats cells on different islands as neighbours, which is
exactly the adjacency the spatial lag model is supposed to encode, and which the blooming
problem (M4) then reinforces.

**Build the mask from BIG's `Area Daratan` layer, foreign polygons included** — see D8 for
why excluding Malaysia would put a false coastline through the middle of Borneo.

**And an archipelago adds a further question:** what *should* adjacency mean across
water? Two cells 15 km apart on opposite sides of a strait are not neighbours by land, but they
may well be neighbours economically — that is what shipping is. Contiguity, distance-decay and
network-distance-over-the-real-transport-network give three different weights matrices and three
different results. **This is a substantive modelling decision for an island economy, not a
default to accept**, and it is a place where the paper could say something other archipelago
studies have not.

## S4. MAUP sensitivity needs origin offsets, not only cell sizes

**Status: Open — a cheap strengthening.**

Running at 5 / 10 / 25 km tests the **scale** effect. MAUP has two components, and the other is
the **zoning** effect: at a fixed cell size, *shifting the grid origin* changes which
observations fall together and can change results on its own (the modifiable areal unit problem). A grid escapes
administrative arbitrariness but not its own arbitrary origin.

**Do this:** at the 10 km baseline, re-run with the origin offset by half a cell in each
direction. Cheap, and it closes the obvious hole in an otherwise careful MAUP section.

---

# Part V — Data integrity

## D1. A layer at the wrong epoch does not announce itself

**Status: Decided — mitigated by `data-register.md`. Keep applying it.**

The session that set this repository up found all three datasets on disk at unusable epochs
(GHS-SMOD 2030, WorldPop 2025/2026) against a design that needs predictors circa 1992–2000 and
outcomes 1992–2020.

**The reason this is in the permanent register and not just the progress log: nothing downstream
catches it.** The raster loads, the CRS is right, the grid aligns, the model fits and reports a
respectable score. A wrong-epoch predictor produces an invalid result that is
indistinguishable, from the output alone, from a fine one. The worst failure is the one that looks like success.

**The mitigation is structural, not attentional:** epoch and licence recorded in
`docs/data-register.md` at download time, because a row filled in later from memory is a guess.

## D2. A classification is not a quantity

**Status: Decided.**

GHS-SMOD is *Degree of Urbanisation*: one class label per cell. GHS-BUILT-S is built-up surface
in m². A growth trajectory can be differenced from the second and not from the first — doing it
from class labels requires deciding how many units of growth a jump from class 12 to class 21
represents, and there is no defensible answer. **The absence of a defensible answer is the tell
that the variable is the wrong type.** SMOD stays useful for the land/water mask and for
descriptives.

## D3. KAPET boundaries may not exist as geometry

**Status: Open — the highest-risk single dependency in the project.**

The validation, which is the paper's credibility anchor, rests entirely on knowing which cells
were designated. Every other Tier A layer is a file on a server; this one may have to be
reconstructed from the designating decrees — and if those define zones as **lists of districts
in 1990s boundaries**, somebody has to source 1990s district geometry. That is *pemekaran*
reappearing at precisely the point the grid design was meant to avoid it.

**Ask the co-authors now, not in month five.** If the answer is "we have the shapefile", a large
risk disappears in one message. If it is not, the work is substantial and belongs in the plan.

## D10. The GHSL rasters were global and unclipped, and the disk filled up

**Status: Decided 2026-10-07 — take Indonesian tiles only, at 100 m.**

The first GHSL downloads were the `GLOBE` files: ~104 GB stored to use the ~1.5% covering
Indonesia, until the disk was full. `GHS_BUILT_S_E2018` alone was 61 GiB plus a 22 GiB overview
pyramid, at 10 m.

**Two separate points, and the second is the one that matters for the analysis.** The disk was
merely an inconvenience. But the 10 m product was also **the wrong resolution for this
design**: at a 10 km unit of analysis, aggregating m² of roof is exact at any input resolution,
so 100 m and 1 km give *identical* cell values at roughly 1/100 and 1/10,000 the size.

**What was done.** The multi-epoch series was taken as the 18 GHSL tiles covering Indonesia
(`R9–R11 × C28–C33`), at 100 m (1 km for SMOD), by `scripts/fetch_ghsl.py`: 28 product-epochs
in 1.8 GB, against 83 GB for the one global 10 m file. The global files were deleted — all
wrong-epoch, all re-downloadable.

**A cost that remains:** Copernicus DEM GLO-30 did not fit on the disk at the time, so terrain
was taken at **GLO-90**. Defensible on its own terms (D11), but forced by storage rather than
chosen by method — worth recording rather than rationalising. GLO-30 would now fit.

## D11. Terrain is the one layer whose epoch does not matter, and GLO-90 is a forced but defensible choice

**Status: Decided 2026-09-12.**

Every other rule-6 worry — *check the epoch before it enters the stack* — is suspended here,
and it is worth saying why rather than letting it look like an oversight. Copernicus DEM is
built from TanDEM-X acquisitions of roughly 2011–2015, which is contemporary, not pre-period.
**That is fine, because mountains do not move.** Terrain is time-invariant at the scale of a
30-year panel, which is precisely the property that makes ruggedness usable as an
**exogenous instrument** (I3): an instrument must be uncorrelated with the outcome except
through the channel of interest, and a variable that cannot change over the study period
cannot have been caused by it.

So terrain is the one layer where a 2011–2015 vintage carries no reverse-causality risk at
all. Flag it in the paper as such, because a careful reader will otherwise apply the same
epoch scepticism the design applies everywhere else.

**GLO-90 rather than GLO-30, and this part was forced.** GLO-30 for the Indonesian tile set is
roughly 19 GB; the disk had 11.9 GB free because of D10. GLO-90 is 1.12 GB. The choice is
defensible on method — at a 10 km unit of analysis, 90 m terrain is ample for ruggedness and
for a coastal-distance surface — but it was made under storage pressure rather than by
argument, and that is worth recording honestly.

**The part that is a real methodological choice, not a storage one:** *ruggedness is
scale-dependent*. A terrain ruggedness index computed at 30 m and then aggregated to 10 km is
not the same number as one computed at 90 m and aggregated. Neither is wrong; they measure
roughness at different scales. So the resolution must be **stated as part of the variable's
definition**, and if GLO-30 is ever substituted after the clip frees space, the instrument
must be re-estimated rather than swapped in — see the MAUP argument in S4, which is the same problem wearing different clothes.

## D4. "Open data" is a claim about licences, not about reachability

**Status: Open — resolve before any BIG layer becomes load-bearing.**

The paper's headline methodological claim is reproducibility, which means every layer must be
redistributable in a replication package, or at minimum fetchable by a stranger running the
script. Two specific items:

- **Badan Informasi Geospasial.** Public services, unclear redistribution terms. Worth settling
  in writing.
- **The mirror at `irpanchumaedi.com`** recorded in the original data notes is a personal blog.
  As provenance for a reproducibility paper it is a weak link: if a layer is taken from there,
  record which BIG product it copies and the date it was taken.

Also, and more mundanely: OpenStreetMap derivatives require attribution — **© OpenStreetMap
contributors**, ODbL — on every map and in the data statement.

## D5. `data/raw/` is immutable, and that is a methodological rule

**Status: Decided.**

A correction to a raw file is a script, never an edit. This looks like hygiene and is actually
about provenance: once a raw file has been hand-fixed, nobody can reconstruct what the provider
supplied, and the pipeline stops being reproducible while continuing to run perfectly. The same
reason generated output (`figures/`, `outputs/`) is never committed — a committed artefact and
the code that makes it drift apart silently, and the artefact wins arguments it should lose.

## D6. Terrain comes from SRTM/Copernicus, and BIG is not a better option

**Status: Decided 2026-09-12 — this question is closed.**

BIG publishes **no national DEM** through `geoservices.big.go.id`; the catalogue was
enumerated in full and the only slope layer is a derived school-siting analysis. Two facts
settle it beyond "we could not find one":

- The RBI sheet index records what BIG's own mapping is built from — `SBR_DATA2` on every
  1:250K sheet reads *"ALOS-AVNIR dan Landsat TM5 tahun 2008-2011, **SRTM 30m dan ASTER
  DEM**"*. **BIG's terrain is SRTM and ASTER.** Taking SRTM or Copernicus DEM directly is the
  upstream source, not a compromise.
- Coverage would be partial regardless: the index's `DTM` field is a flag, not a link, and
  only **62 of 309** sheets have one.

DEMNAS, the proper national DEM, is behind a browser-only portal and would be a manual
per-tile job. Against an openly downloadable, globally consistent, already-planned
alternative, it does not earn the effort unless a specific analysis needs sub-30 m terrain —
and nothing on a 10 km grid does.

**The general point, which is the reusable part:** "the national agency must have better data
than the global product" is an assumption worth testing rather than believing. Here the
national product *is* the global product, reprocessed.

## D7. BIG's GeoJSON output is not trustworthy at the page level, and one bad feature hid 999

**Status: Decided — handled in `scripts/fetch_big.py`. Recorded as a pattern.**

The land-polygon layer failed at `offset 16000` with a bare `400 Failed to execute query`.
Bisecting the object-id range found a single feature, `OBJECTID 16692` — a polygon whose four
points all lie on one meridian, three distinct collinear positions, `Shape_Area: 0`, about 44
cm long. A zero-area sliver, invalid as GeoJSON, which BIG's GeoJSON serialiser rejects and
its Esri-JSON serialiser emits without complaint.

Three things in that worth keeping:

1. **A whole page failed because of one feature**, and the error message named neither the
   feature nor the reason. An opaque 400 from a GIS server is worth bisecting rather than
   working around.
2. **The format was the problem, not the data.** `f=json` works where `f=geojson` fails, so
   the fix is a client-side conversion rather than a lost feature.
3. **Degenerate geometry is kept and counted, never dropped.** Dropping it would have made the
   feature count match while changing the data, which is the failure this pipeline is built to
   prevent. It is reported instead, so it can be cleaned with `make_valid` at the point of use.

## D8. BIG's layers include neighbouring countries

**Status: Decided — filter on `NEGARA`, but know which way the default cuts.**

The coastline and land layers extend to 7.125°N, past Indonesia's northern limit of about
5.9°N. Not a CRS fault: the land layer's own `NEGARA` attribute reports **17,075 Indonesia,
127 Malaysia, 28 Singapore, 27 Timor-Leste**, and three coastline features named *Garis Pantai
Malaka* run up the strait into Malaysia and Thailand.

**Which default is right depends on the use, and the two uses disagree:**

- For the **land mask** (S3), keep the foreign polygons. Borneo is shared with Malaysia and
  Brunei; masking Indonesia alone would cut an island in half and put a false coastline
  through the middle of it, which is precisely the fictitious-adjacency problem the mask
  exists to fix.
- For anything **describing Indonesian territory** — cell counts, area totals, "n grid cells
  in the study area" — filter to `NEGARA = 'INDONESIA'`, or the numbers include Johor.

The 28 Singapore polygons are incidentally useful: Batam's adjacency to Singapore is the
anchor case in T4, and it is now in the data rather than in a footnote.

**Why those three neighbours and not the fourth.** The layer comes from BIG's *bathymetry*
service, where `Area Daratan` exists to bound the sea for nautical charting — a chart of the
Malacca Strait that stopped at the median line would be useless to a ship. So the land that
fronts charted Indonesian water is included. The cut is at **141°E**, which is precisely the
Indonesia&ndash;Papua New Guinea border: Malaysia (99.2&ndash;119.3°E), Singapore
(103.6&ndash;104.1°E) and Timor-Leste (124.0&ndash;127.3°E) all lie west of it and share a
sea or an island; PNG lies entirely east of it and is the one neighbour absent. The clearest
case is **Sebatik**, which appears under `NEGARA = MALAYSIA` — an island split down the
middle between the two countries, so Indonesian Sebatik cannot be drawn without the Malaysian
half beside it.

## D9. The land layer encodes water two different ways, and a naive mask gets one of them wrong

**Status: Open — resolve before building the land mask.**

`Area Daratan` represents inland water inconsistently. **217 polygons carry interior rings**
(a lake as a hole in the land, which is what a mask wants), and **496 separate polygons are
named `TOPONIM = DANAU`** ("lake") as standalone positive features.

Rasterise "every polygon is land" and the second group is filled in **as land**, so 496 lakes
silently become buildable ground. None is large — the biggest is about 90 km², well under Lake
Toba — so the error is small, invisible, and exactly the kind that survives review.

**Do this:** when building the mask (S3), subtract features whose `TOPONIM` is `DANAU`, and
cross-check the result against the separate `big_250k_danau_lakes.geojson` layer, which holds
802 lake polygons from the 1:250K atlas. Two independent sources for the same feature class is
a free validation; report how many lakes each contains and whether they agree.

## D12. A file's declared nodata is not the whole story, and resampling is where that bites

**Status: Decided — both instances fixed. Recorded because the pattern will recur.**

Two rasters produced confidently wrong pictures on 2026-09-12, from the same root cause in two
different disguises: **absence of data encoded as something other than the declared nodata.**

**(a) Nodata averaged into real values.** `GHS_BUILT_S_E2018` is `uint8` with `nodata=255` and
a *physical* maximum of 100 — m² of roof in a 10 m cell. A decimated `average` read mixes
nodata into neighbouring cells, so ocean-255 averaged against coastal land produced values of
101–254. Those are impossible, but nothing rejected them, and they rendered as built-up across
**56.6% of the frame** in a country that is ~23% land. The picture looked like a plausible
development map.

**(b) Absence encoded as a valid value.** Copernicus DEM fills the sea with **0 m**, not
nodata. Zero cannot be filtered by value, because zero is also a perfectly good elevation for a
coastal plain. The terrain mosaic covered 55.2% of the frame until a land mask was applied.

**The general rule this yields, which is worth carrying into the pipeline:** *check every layer
against its physical range and its expected spatial extent, not only against its declared
nodata.* A value outside what the quantity can physically be is nodata whatever the header
says; and a layer whose coverage does not match the study area's land fraction is telling you
something before you have plotted anything.

**The cheap check that caught both**, and that cost nothing: **land fraction**. Indonesia's
land in this frame is about 23%, and three unrelated sources agree closely — rasterised BIG
polygons 22.9%, GHS-SMOD 22.6%, GHS-WUP DEGURBA 22.7%. Any layer reporting far more than that
is covering sea. Add a coverage figure to every layer the pipeline produces; it is one number
and it catches a whole class of silent error.

## D13. A categorical layer whose class codes you have not checked will render blank and report success

**Status: Decided — fixed, and the fix is to fail rather than to draw nothing.**

`IDN_DUG_2026_GRID_L1` uses class codes **1/2/3**. Every other degree-of-urbanisation layer in
this project — GHS-SMOD, GHS-WUP DEGURBA, and WorldPop's own L2 grid — uses the GHSL codes
10/11/12/13/21/22/23/30. Applying the GHSL table to L1 matched **no pixel at all**, so the
renderer produced a valid, fully transparent image and exited 0.

**That failure is worse than a crash, because a blank overlay is indistinguishable from "there
is no data here".** In a study of an archipelago, "nothing in this region" is a claim a reader
would accept without blinking.

Two things follow. First, the renderer now **raises** when a categorical layer matches zero
pixels, and prints the values actually present. Second, and more general: **a class code is
metadata that must be read from the data, never inherited from a sibling product.** Same
agency, same variable name, same year, adjacent file — different encoding. Check
`np.unique` before writing a colour table.

## D14. "Physical geography" layers are not all time-invariant — reservoirs and reclaimed coast are built

**Status: Watch — becomes live when the water and coast layers enter the predictor stack.**

Terrain is exempt from the epoch rule because mountains do not move (D11). It is tempting to
extend the same exemption to every BIG water and coast layer, since they *look* like physical
geography. Two of them are partly man-made, and the man-made part is dated:

- **Lakes (`big_250k_danau_lakes`) include *Waduk* — reservoirs.** A reservoir is
  infrastructure. One completed after 2000 sits in a 2013 layer and would enter a "pre-period"
  water-supply predictor as if it had been there all along — and dams are often built *because*
  a region was growing, which is the reverse causality the staging exists to remove.
- **The coastline (`big_250k_garis_pantai_coastline`, 2013) includes land reclamation.**
  Batam and North Jakarta, both central cases here, reclaimed coast after 2000. For coastal
  distance as an *instrument* this is at worst a few hundred metres and probably harmless at a
  10 km cell; for natural-harbour geometry near a reclaimed port, it is worth checking.

Rivers, basins, groundwater potential and bathymetry are natural to a good approximation.

**What to do when it goes live:** either drop the reservoirs from the pre-period water layer
(keep natural lakes only), or date them against a dam register; and spot-check the coastline at
the reclaimed sites against an older source (GEBCO or a 1990s Landsat scene). Noticed
2026-10-07, while sorting the on-disk data into "redownload" and "keep".

## F1. Prediction and explanation are different goals, and the paper should say which is which

**Status: Decided — cite it.**

Tier 2 runs a gradient-boosted surface **and** a spatial panel. Presented without comment this
reads as belt-and-braces. It is not: prediction and explanation are different objectives with
different standards, and a model optimised for one is not automatically good at the other. The
canonical reference is Shmueli (2010), *To Explain or to Predict?*, Statistical Science.

Citing it converts "we did both" into a defended design choice, and it licenses the division of
labour the paper already intends: **the ML surface is the prescriptive product, the econometrics
is the referee-defensible core.** One sentence, one citation, and a reviewer's "why two models?"
is answered before it is asked.

## F2. The weakest input sets the fragility of the conclusion

**Status: Decided — and worth stating as a principle, because it already shaped the design.**

Minimum-viable-bundle optimisation was dropped because credible infrastructure unit costs for
Indonesia are not openly available, and keeping it would have made the headline result hostage
to the worst data in the pipeline. The residual-and-binding-constraint reframing recovers most
of the policy insight on Tier A data alone.

**The general rule: a conclusion is as fragile as its weakest input, not as strong as its
average one.** It is why the tier structure exists, and it is the right answer to any future
suggestion that the paper would be more impressive with one more fragile layer bolted on — for
instance the climate extension discussed in `data-register.md` §5, which is a good idea for a
different paper.

## F3. Which venue leads is a framing decision, and it is cheaper to make early

**Status: Open.**

Four venues are ranked in the proposal, and the same analysis supports all of them with a shift
of emphasis — *Computers, Environment and Urban Systems* (reproducible method), *Applied
Geography* (applied spatial analysis), *Papers in Regional Science* (identification foregrounded),
a development journal (the Indonesia policy angle). The framing determines what gets emphasised
and how much space identification versus pipeline gets.

**Decide before drafting, not during.** Re-framing a finished draft is much more work than
writing to a target, and for a first paper the version that gets written is usually the version
that gets submitted.

## F4. Process items that are not methodology but will cost more if left

**Status: Open.**

Not strictly in scope for this file, recorded because they become harder with time: **division
of labour and authorship order** are not written down anywhere, and they are an easy
conversation now and an awkward one at submission. Likewise, the **reproducibility claim implies
a commitment** — the replication package has to actually run on someone else's machine, which is
a task with a cost, not a property the repo acquires by being public.

---

## Adding to this file

An entry earns a place if it is something a **referee could raise**, or something that would
**change a result if got wrong**. Write it when it is noticed, not when it is resolved —
an entry that says "Open, no answer yet" is doing its job. When something is settled, change the
status to **Decided** and keep the reasoning, so that it is not re-argued from scratch in six
months.
