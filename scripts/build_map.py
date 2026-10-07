#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "geopandas>=1", "pyogrio"]
# ///
"""
Build a self-contained interactive HTML map of everything collected so far.

    uv run --script scripts/build_raster_overlays.py   # first, if a raster changed
    uv run --script scripts/build_map.py

Writes map/index.html — one file, no network requests, opens from disk.

The layers come from config/map_layers.yaml, not from this file. To put a new
dataset on the map, add an entry there and rebuild; the code does not change.
Any vector format GDAL reads works (.geojson, .gpkg with `layer:`, .shp), in
any CRS — non-GeoJSON sources are reprojected to lon/lat on the way in.

Why this is not just "load the GeoJSON into Leaflet"
----------------------------------------------------
The raw layers are 85 MB and about 1.8 million vertices. A browser will not draw
that; it will hang. So the map is built from a *display copy* — simplified,
rounded, and split into sensible layers — and the raw files are never touched.

That distinction matters beyond performance. This map is for LOOKING at the data,
which is the one job a script cannot do: `check_geojson.py` can tell you a layer's
extent is wrong, but only an eye can tell you the road network has a hole over
Sulawesi. Nothing here is analysis, and no output of it should be measured.
Every layer says how decimated it is, so the map cannot be mistaken for the data.

Two deliberate choices
----------------------
* **Douglas-Peucker at ~550 m**, written out longhand below. It keeps
  endpoints, so lines stay connected.
* **Roads split by class.** Not only because 136,810 features is too many to draw
  at once, but because the split IS a finding: `Jalan Lain` ("other") is 59% of
  network length, and toggling it on and off shows what the classified network
  actually covers. See considerations M7.
"""

from __future__ import annotations

import base64
import json
import math
import os
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "map_layers.yaml"
OUT = ROOT / "outputs" / "map"          # raster PNGs from build_raster_overlays.py
# Two pages from every build. The SHARED one is committed; it never contains a
# layer marked `local_only: true` in the config (data whose licence does not yet
# allow redistribution). The FULL one has everything and stays on this machine
# (outputs/ is git-ignored). Writing both every time means nobody has to remember
# a flag before committing — the committed file simply cannot hold those layers.
HTML_OUT = ROOT / "map" / "index.html"               # shared, committed
HTML_FULL = ROOT / "outputs" / "map" / "index.html"  # full, local only

# GitHub warns about files over 50 MB and rejects them over 100 MB. The page is
# committed, so the build refuses to write anything that would trigger either.
MAX_MB = 50

# Display tolerance in degrees. 0.005 deg is roughly 550 m at the equator — far
# below what is visible on a map of a 5,000 km wide country, and far above the
# vertex spacing of a 1:250,000 source.
TOL = 0.005
PRECISION = 3          # ~110 m, matched to TOL. Small features get 5 (~1 m).


# ---------------------------------------------------------------- geometry ---

def perp_distance(p, a, b) -> float:
    """Perpendicular distance from point p to the segment a-b, in degrees."""
    (px, py), (ax, ay), (bx, by) = p[:2], a[:2], b[:2]
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def simplify(points: list, tol: float) -> list:
    """Douglas-Peucker, iterative so a long line cannot blow the recursion limit.

    Keeps the first and last point of every line, which is what makes a
    simplified road network still connect to itself.
    """
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi <= lo + 1:
            continue
        worst, worst_i = -1.0, lo
        for i in range(lo + 1, hi):
            d = perp_distance(points[i], points[lo], points[hi])
            if d > worst:
                worst, worst_i = d, i
        if worst > tol:
            keep[worst_i] = True
            stack.append((lo, worst_i))
            stack.append((worst_i, hi))
    return [p for p, k in zip(points, keep) if k]


def round_pt(p, precision: int = PRECISION):
    return [round(p[0], precision), round(p[1], precision)]


def bbox_span(points: list) -> float:
    """Diagonal of a ring's bounding box, in degrees."""
    xs = [q[0] for q in points]
    ys = [q[1] for q in points]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys))


def thin_ring(ring: list, tol: float, closed: bool) -> list | None:
    """Simplify one ring or path. Returns None if it collapses to nothing.

    A small RING is not simplified. Douglas-Peucker on a 300 m island at a 550 m
    tolerance returns two points, which is not a polygon, and it deleted 82% of
    Indonesia's land polygons on the first attempt. Small rings are also the cheap
    ones — few vertices by definition — so keeping them whole costs little. They
    get an extra decimal place too, since 11 m rounding can itself collapse a very
    small island.

    The exemption applies ONLY to rings. A line has no minimum vertex count to
    stay valid, and extending the exemption to lines made things worse, not
    better: most road segments are shorter than the tolerance, so almost the whole
    network skipped simplification and the output grew by half.
    """
    # A LineString whose first point equals its last is an island outline drawn
    # as a line: it collapses exactly as a ring does, so it gets the same
    # exemption. Without this the coastline layer lost 5,249 small islands.
    ring_like = closed or (len(ring) > 2 and ring[0][:2] == ring[-1][:2])
    span = bbox_span(ring)
    if ring_like and span < tol * 3:
        prec = min(PRECISION + 2, 6)
        out = [round_pt(p, prec) for p in ring]
    else:
        out = [round_pt(p) for p in simplify(ring, tol)]
    # De-duplicate consecutive identical points produced by rounding.
    dedup = [out[0]] if out else []
    for p in out[1:]:
        if p != dedup[-1]:
            dedup.append(p)
    if closed:
        if len(dedup) < 3:
            return None
        if dedup[0] != dedup[-1]:
            dedup.append(dedup[0])
        # A ring needs 3 distinct positions to enclose any area at all.
        if len({tuple(p) for p in dedup}) < 3:
            return None
    elif len(dedup) < 2:
        return None
    return dedup


def thin_geometry(geom: dict, tol: float) -> dict | None:
    """Simplify any GeoJSON geometry, dropping parts that collapse."""
    if not geom:
        return None
    t, c = geom.get("type"), geom.get("coordinates")
    if not c:
        return None

    if t == "LineString":
        r = thin_ring(c, tol, False)
        return {"type": t, "coordinates": r} if r else None

    if t == "MultiLineString":
        parts = [r for r in (thin_ring(p, tol, False) for p in c) if r]
        return {"type": t, "coordinates": parts} if parts else None

    if t == "Polygon":
        rings = [r for r in (thin_ring(p, tol, True) for p in c) if r]
        # If the exterior ring collapsed the whole polygon is gone; holes alone
        # are meaningless, so drop them too.
        return {"type": t, "coordinates": rings} if rings else None

    if t == "MultiPolygon":
        polys = []
        for poly in c:
            rings = [r for r in (thin_ring(p, tol, True) for p in poly) if r]
            if rings:
                polys.append(rings)
        return {"type": t, "coordinates": polys} if polys else None

    if t == "Point":
        return {"type": t, "coordinates": round_pt(c)}
    if t == "MultiPoint":
        return {"type": t, "coordinates": [round_pt(p) for p in c]}
    return None


def count_vertices(geom: dict) -> int:
    def walk(c):
        if not c:
            return 0
        if isinstance(c[0], (int, float)):
            return 1
        return sum(walk(x) for x in c)
    return walk(geom.get("coordinates"))


# ------------------------------------------------------------------- build ---

_CACHE: dict[str, dict] = {}


def load(rel: str, layer: str | None = None) -> dict | None:
    """Read a source file as a GeoJSON dict in lon/lat, or None if missing.

    Cached — the 40 MB road file feeds seven display layers and parsing it
    seven times is pure waste. GeoJSON is read directly (fast, and it is
    lon/lat by definition); anything else goes through GDAL and is
    reprojected to EPSG:4326, because Leaflet only speaks lon/lat.
    """
    key = (rel, layer)
    if key in _CACHE:
        return _CACHE[key]
    path = ROOT / rel
    if not path.exists():
        return None
    if path.suffix.lower() in (".geojson", ".json") and layer is None:
        with open(path) as fh:
            fc = json.load(fh)
    else:
        import geopandas as gpd  # only needed for non-GeoJSON sources
        gdf = gpd.read_file(path, layer=layer)
        if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(4326)
        fc = json.loads(gdf.to_json(drop_id=True))
    _CACHE[key] = fc
    return fc


def make_filter(spec: dict | None):
    """Turn a YAML `filter:` into a test on a feature's properties."""
    if not spec:
        return None
    field = spec["field"]
    if "in" in spec:
        allowed = set(spec["in"])
        return lambda p: p.get(field) in allowed
    if "startswith" in spec:
        prefix = spec["startswith"]
        return lambda p: str(p.get(field) or "").startswith(prefix)
    raise ValueError(f"unknown filter {spec}: use `in:` or `startswith:`")


VECTOR_KEYS = {"name", "path", "layer", "group", "kind", "color", "weight", "dash",
               "props", "filter", "visible", "tol", "ground", "note", "credit", "local_only"}


def build_layer(spec: dict) -> dict | None:
    """Simplify one source layer (optionally filtered) into a display layer."""
    unknown = set(map(str, spec)) - VECTOR_KEYS
    if unknown:
        # A misspelt key would otherwise be ignored without a word — and YAML
        # turns a bare `on:` into the boolean True, which shows up here as "True".
        raise SystemExit(f"layer '{spec.get('name')}': unknown key(s) {sorted(unknown)}")
    name, kind = spec["name"], spec["kind"]
    fc = load(spec["path"], spec.get("layer"))
    if fc is None:
        print(f"  MISSING  {spec['path']} — '{name}' skipped")
        return None
    where = make_filter(spec.get("filter"))
    keep_props = spec.get("props", [])
    tol = spec.get("tol", TOL)
    feats_in = fc.get("features", [])
    out, v_in, v_out, dropped = [], 0, 0, 0

    for f in feats_in:
        props = f.get("properties") or {}
        if where and not where(props):
            continue
        g = f.get("geometry")
        v_in += count_vertices(g or {})
        g2 = thin_geometry(g, tol)
        if not g2:
            dropped += 1
            continue
        v_out += count_vertices(g2)
        out.append({"t": g2["type"], "c": g2["coordinates"],
                    "p": {k: props.get(k) for k in keep_props if props.get(k) not in (None, "")}})

    print(f"  {name:<34} {len(out):>7,} feats  "
          f"{v_in:>8,} -> {v_out:>7,} verts  dropped {dropped}")
    return {"name": name, "group": spec["group"], "color": spec.get("color", "#555"),
            "kind": kind, "dash": spec.get("dash"), "weight": spec.get("weight", 1.2),
            "note": spec.get("note", ""), "ground": spec.get("ground", False),
            "on": spec.get("visible", True), "n": len(out),
            "credit": spec.get("credit", ""), "local_only": bool(spec.get("local_only")),
            "dropped": dropped, "verts": v_out, "f": out}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print("Building display copies (raw files are not touched)\n")

    cfg = yaml.safe_load(CONFIG.read_text())
    layers = [l for l in (build_layer(v) for v in cfg.get("vectors", [])) if l]

    # Raster overlays, if build_raster_overlays.py has been run. The PNGs are
    # EMBEDDED in the page as base64 data: URIs rather than referenced by path.
    # A relative path only works while rasters/ travels beside index.html, and a
    # colleague who is sent just the .html would get an empty raster list with
    # no error. Embedding costs a third extra in size (base64 turns 3 bytes into
    # 4) and buys a page that is one file.
    man = OUT / "rasters" / "manifest.json"
    rasters = json.loads(man.read_text()) if man.exists() else []
    embed = lambda f: "data:image/png;base64," + base64.b64encode((OUT / f).read_bytes()).decode()
    raster_cfg = {r["name"]: r for r in cfg.get("rasters", [])}
    for r in rasters:
        spec = raster_cfg.get(r["name"], {})
        r["credit"] = spec.get("credit", "")
        r["local_only"] = bool(spec.get("local_only"))
        r["file"] = embed(r["file"])
        for step in r.get("series", []):
            step["file"] = embed(step["file"])
    print(f"\n  raster overlays found: {len(rasters)}"
          + ("" if rasters else "  (run scripts/build_raster_overlays.py)"))

    vendor = pathlib.Path(__file__).resolve().parent / "vendor"
    builds = [
        ("shared", HTML_OUT,
         [l for l in layers if not l["local_only"]], [r for r in rasters if not r["local_only"]]),
        ("full", HTML_FULL, layers, rasters),
    ]
    for label, out_file, lyrs, rasts in builds:
        # Credit exactly the sources drawn on THIS page, in order, without repeats.
        credits = list(dict.fromkeys(x["credit"] for x in [*lyrs, *rasts] if x["credit"]))
        payload = {"groups": cfg["groups"], "layers": lyrs, "rasters": rasts,
                   "credits": credits, "tol_deg": TOL, "precision": PRECISION}
        # "<" is escaped so the payload can never close its own <script> tag.
        data_js = json.dumps(payload, separators=(",", ":")).replace("<", "\\u003c")

        # Leaflet is vendored and inlined rather than pulled from a CDN: the page
        # then makes no network requests at all, works offline, and cannot break
        # because a CDN changed. It is ~158 kB against a ~30 MB page.
        html = (HTML_TEMPLATE
                .replace("__LEAFLET_CSS__", (vendor / "leaflet.min.css").read_text())
                .replace("__LEAFLET_JS__", (vendor / "leaflet.min.js").read_text())
                .replace("__DATA__", data_js))
        size_mb = len(html.encode("utf-8")) / 1e6
        if label == "shared" and size_mb > MAX_MB:
            print(f"\n  REFUSED: page would be {size_mb:.1f} MB, over the {MAX_MB} MB limit "
                  "for a file committed to GitHub. Raise `tol` on heavy vector layers or "
                  "drop a raster.", file=sys.stderr)
            return 1
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(html, encoding="utf-8")

        held = [x["name"] for x in [*layers, *rasters] if x not in lyrs and x not in rasts]
        print(f"\n  {label.upper()}: {len(lyrs)} vector + {len(rasts)} raster layers, "
              f"{sum(l['n'] for l in lyrs):,} features")
        if held:
            print(f"  left out as local_only: {', '.join(held)}")
        print(f"  WROTE {out_file.relative_to(ROOT)}  ({size_mb:.1f} MB)")

    print(f"\n  open with:  xdg-open {HTML_FULL.relative_to(ROOT)}   (everything)")
    return 0


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Indonesia SEZ+GIS — data collected</title>
<style>__LEAFLET_CSS__</style>
<script>__LEAFLET_JS__</script>
<style>
  :root{
    --bg:#f7f6f3; --panel:#fff; --ink:#1d1d1f; --muted:#6b6b70;
    --line:#e2e0da; --accent:#b4530a;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;font:13px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg)}
  #app{display:flex;height:100vh;overflow:hidden}
  #side{width:340px;flex:0 0 340px;background:var(--panel);border-right:1px solid var(--line);
        overflow-y:auto;padding:16px 16px 40px}
  #map{flex:1;height:100%;background:#cfdde6}   /* ocean, since there are no tiles */
  .leaflet-container{background:#cfdde6}
  h1{font-size:15px;margin:0 0 2px;letter-spacing:-.01em}
  .sub{color:var(--muted);font-size:11.5px;margin:0 0 14px}
  h2{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
     margin:18px 0 7px;padding-bottom:5px;border-bottom:1px solid var(--line)}
  .lyr{display:flex;gap:8px;align-items:flex-start;padding:5px 6px;border-radius:5px;cursor:pointer}
  .lyr:hover{background:#f2f1ec}
  .lyr input{margin:3px 0 0}
  .sw{width:11px;height:11px;flex:0 0 11px;border-radius:2px;margin-top:4px;border:1px solid rgba(0,0,0,.18)}
  .nm{flex:1;min-width:0}
  .nm b{font-weight:530;display:block}
  .cnt{color:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
  .note{display:none;color:var(--muted);font-size:11.5px;margin:4px 0 6px 25px;
        padding-left:9px;border-left:2px solid var(--line)}
  .lyr.open + .note{display:block}
  .warn{background:#fdf3e7;border:1px solid #f0d9bd;border-radius:6px;padding:9px 11px;
        font-size:11.5px;margin:10px 0}
  .warn b{color:var(--accent)}
  table{width:100%;border-collapse:collapse;font-size:11.5px}
  td{padding:3px 0;vertical-align:top;border-bottom:1px solid #f0efe9}
  td:last-child{text-align:right;color:var(--muted);white-space:nowrap;padding-left:8px;
                font-variant-numeric:tabular-nums}
  .btn{background:#fff;border:1px solid var(--line);border-radius:5px;padding:4px 9px;
       font:inherit;font-size:11.5px;cursor:pointer;margin:0 4px 6px 0}
  .btn:hover{border-color:#c9c6bd;background:#faf9f6}
  .epoch{display:flex;align-items:center;gap:8px;margin:-2px 0 6px 25px;font-size:11.5px}
  .epoch input{flex:1}
  .epoch b{font-variant-numeric:tabular-nums;min-width:32px}
  .leaflet-popup-content{font:12px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:9px 11px}
  .leaflet-popup-content h4{margin:0 0 5px;font-size:12px}
  .leaflet-popup-content td{padding:1px 0}
  @media (max-width:760px){#app{flex-direction:column}#side{width:100%;flex:0 0 auto;max-height:42vh;
    border-right:0;border-bottom:1px solid var(--line)}#map{flex:1}}
</style></head><body>
<div id="app">
  <div id="side">
    <h1>Indonesia SEZ+GIS</h1>
    <p class="sub">Everything collected so far. Click a layer name to read what it is.
      <b>No basemap</b>, deliberately: nothing underneath can fill in a gap in our own
      data.</p>
    <div>
      <button class="btn" id="allOn">All on</button>
      <button class="btn" id="allOff">All off</button>
      <button class="btn" id="reset">Reset view</button>
    </div>
    <div id="groups"></div>
    <h2>What this map is not</h2>
    <p class="sub" style="margin:0">
      A display copy. Geometry is simplified with Douglas&ndash;Peucker at
      <b id="tolv"></b>&deg; (~550&nbsp;m) and coordinates rounded to
      <b id="precv"></b> decimals, so it draws in a browser, and rasters are resampled
      to screen resolution. <b>Do not measure anything off it.</b> The source
      files are untouched.
    </p>
  </div>
  <div id="map"></div>
</div>
<script id="payload" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);

const IDN = [[-11.2, 94.8],[6.3, 141.2]];
const map = L.map('map', {preferCanvas:true, zoomControl:true}).fitBounds(IDN);
// Top right: the attribution strip along the bottom wraps to two lines and
// would sit on top of a bottom-left scale bar.
L.control.scale({imperial:false, position:'topright'}).addTo(map);

// No basemap tiles. OpenStreetMap's tile usage policy requires a valid
// identifying Referer/User-Agent, which a page opened from file:// cannot send,
// so their CDN blocks it — correctly. Using a tile provider in breach of its
// policy is not an option, and none is needed: the land polygons ARE the
// basemap. That is better for this map's purpose anyway, because an OSM basemap
// draws its own road network underneath BIG's, and then a gap in BIG's coverage
// is invisible — filled in by somebody else's data.
// Four panes, bottom to top: the opaque land polygons, then terrain relief,
// then the agglomeration rasters, then every other vector (Leaflet's own
// overlayPane, z-index 400). bringToBack only reorders WITHIN a pane, so each
// of these needs a pane of its own: the ground would otherwise hide the rasters
// completely, and terrain would cover whichever agglomeration layer was
// switched on before it.
map.createPane('ground');
map.getPane('ground').style.zIndex = 210;
map.createPane('terrain');
map.getPane('terrain').style.zIndex = 230;
map.createPane('rasters');
map.getPane('rasters').style.zIndex = 250;

// Every source that is drawn gets credited. The Copernicus wording is the
// licence's required text, not a paraphrase.
L.control.attribution({prefix:false})
  // Built from the `credit` of each layer actually on this page (config/map_layers.yaml).
  .addAttribution('Data: ' + (DATA.credits || []).join(' &middot; ')
    + ' &middot; no basemap, by design')
  .addTo(map);

function popup(name, p){
  let rows = Object.entries(p).map(([k,v]) =>
    `<tr><td style="color:#6b6b70;padding-right:9px">${k}</td><td><b>${v}</b></td></tr>`).join('');
  if(!rows) rows = '<tr><td style="color:#6b6b70">no attributes</td></tr>';
  return `<h4>${name}</h4><table>${rows}</table>`;
}

// ---- vector layers ---------------------------------------------------------
// Whether a layer starts switched on is set per layer in config/map_layers.yaml
// (`visible: false` for the heavy ones).
const made = [];
DATA.layers.forEach(L_ => {
  const isPoly = L_.kind === 'polygon';
  const style = isPoly
    ? (L_.ground
        // The ground layer is opaque: it stands in for a basemap.
        ? {color:'#b9b1a0', weight:.4, opacity:1, fillColor:L_.color, fillOpacity:1}
        : {color:L_.color, weight:.6, opacity:.9, fillColor:L_.color, fillOpacity:.35})
    : {color:L_.color, weight:L_.weight, opacity:.95, dashArray:L_.dash || null};
  const fc = {type:'FeatureCollection', features:L_.f.map(f =>
    ({type:'Feature', geometry:{type:f.t, coordinates:f.c}, properties:f.p}))};
  const lyr = L.geoJSON(fc, {
    style: () => style,
    // Points (ports, site anchors) are drawn as small circles rather than
    // Leaflet's default pin images, which would need image files.
    pointToLayer: (feat, latlng) => L.circleMarker(latlng,
      {radius:4, color:'#fff', weight:1, fillColor:L_.color, fillOpacity:.95}),
    pane: L_.ground ? 'ground' : 'overlayPane',
    onEachFeature: (feat, l) => l.bindPopup(() => popup(L_.name, feat.properties))
  });
  made.push({def:L_, lyr});
  if(L_.on) lyr.addTo(map);
});

// Within the overlay pane, polygons go behind lines so a road is never hidden
// by a catchment. The ground layer is not touched: it is in its own pane.
function restack(){
  made.filter(m => m.def.kind === 'polygon' && !m.def.ground)
      .forEach(m => m.lyr.bringToBack && m.lyr.bringToBack());
}
restack();

// ---- raster overlays -------------------------------------------------------
// Terrain (group "land") sits in its own pane just above the land polygons, so
// every other layer draws on top of it, at a fixed opacity. All other rasters
// share one pane and one opacity slider.
const rasterMade = [];
(DATA.rasters || []).forEach(r => {
  const isTerrain = r.group === 'land';
  const lyr = L.imageOverlay(r.file, r.bounds,
    {opacity: isTerrain ? .8 : .75, pane: isTerrain ? 'terrain' : 'rasters'});
  rasterMade.push({def:r, lyr});
});

function legendHTML(r){
  const g = r.legend || {};
  if(g.kind === 'classes')
    return '<div style="margin:6px 0 2px">' + g.classes.map(c =>
      `<span style="display:inline-block;margin:0 7px 3px 0;white-space:nowrap">
         <i style="display:inline-block;width:9px;height:9px;background:${c.color};
            border-radius:2px;vertical-align:middle;margin-right:3px"></i>${c.label}</span>`
      ).join('') + '</div>';
  if(g.kind === 'continuous'){
    const bar = g.ramp.map(c => `<i style="flex:1;height:8px;background:${c}"></i>`).join('');
    const scope = r.series ? 'one scale for every epoch' : '2nd&ndash;99.5th pct';
    return `<div style="margin:6px 0 2px">
      <div style="display:flex;border-radius:2px;overflow:hidden">${bar}</div>
      <div style="display:flex;justify-content:space-between;font-size:10.5px;color:#6b6b70">
        <span>low</span><span>high (log scale, ${scope})</span></div></div>`;
  }
  return '';
}

const host = document.getElementById('groups');

// One sidebar row for a raster. A time series gets an epoch slider that swaps
// the image inside the same overlay, so switching years keeps its place in the
// draw order and its opacity.
function rasterRow(m){
  const d = m.def;
  const ramp = (d.legend && d.legend.ramp) || ['#fdbe85','#7f2704'];
  const row = document.createElement('div');
  row.className = 'lyr';
  const res = d.src_res < 1 ? d.src_res.toFixed(5) + '&deg;' : d.src_res + ' m';
  row.innerHTML = `<input type="checkbox">
    <span class="sw" style="background:linear-gradient(90deg,${ramp[0]},${ramp[ramp.length-1]})"></span>
    <span class="nm"><b>${d.name}</b>
      <span class="cnt">${d.crs} &middot; source res ${res} &middot;
        ${(d.coverage*100).toFixed(1)}% of frame</span></span>`;
  const box = row.querySelector('input');
  box.addEventListener('click', e => e.stopPropagation());
  box.addEventListener('change', () => {
    if(box.checked) m.lyr.addTo(map); else map.removeLayer(m.lyr);
  });
  row.addEventListener('click', () => row.classList.toggle('open'));
  const note = document.createElement('div');
  note.className = 'note';
  note.innerHTML = (d.note || '') + legendHTML(d);
  host.appendChild(row); host.appendChild(note);

  if(d.series){
    const n = d.series.length;
    const ctl = document.createElement('div');
    ctl.className = 'epoch';
    ctl.innerHTML = `<input type="range" min="0" max="${n-1}" value="${n-1}" step="1">
      <b>${d.series[n-1].epoch}</b>`;
    const slider = ctl.querySelector('input'), label = ctl.querySelector('b');
    slider.addEventListener('input', () => {
      const step = d.series[+slider.value];
      m.lyr.setUrl(step.file);
      label.textContent = step.epoch;
      // Moving the slider is a request to see the layer.
      if(!box.checked){ box.checked = true; m.lyr.addTo(map); }
    });
    host.appendChild(ctl);
  }
  m.box = box;
}

function vectorRow(m){
  const on = map.hasLayer(m.lyr);
  const row = document.createElement('div');
  row.className = 'lyr';
  row.innerHTML = `<input type="checkbox" ${on?'checked':''}>
    <span class="sw" style="background:${m.def.color}"></span>
    <span class="nm"><b>${m.def.name}</b>
      <span class="cnt">${m.def.n.toLocaleString()} features &middot; ${m.def.verts.toLocaleString()} vertices</span>
    </span>`;
  const note = document.createElement('div');
  note.className = 'note';
  note.innerHTML = m.def.note || '<i>No notes on this layer.</i>';
  const box = row.querySelector('input');
  box.addEventListener('click', e => e.stopPropagation());
  box.addEventListener('change', () => {
    if(box.checked){ m.lyr.addTo(map); restack(); }
    else map.removeLayer(m.lyr);
  });
  row.addEventListener('click', () => row.classList.toggle('open'));
  host.appendChild(row); host.appendChild(note);
  m.box = box;
}

// Sidebar sections come from config/map_layers.yaml, in the order listed there.
// A section with nothing in it (e.g. Ports before that data exists) is hidden.
let sliderShown = false;
DATA.groups.forEach(g => {
  const vec = made.filter(m => m.def.group === g.id);
  const ras = rasterMade.filter(m => m.def.group === g.id);
  if(!vec.length && !ras.length) return;
  host.insertAdjacentHTML('beforeend', `<h2>${g.title}</h2>`);
  if(g.warn) host.insertAdjacentHTML('beforeend', `<div class="warn">${g.warn}</div>`);
  if(ras.some(m => m.def.group !== 'land') && !sliderShown){
    host.insertAdjacentHTML('beforeend',
      `<div style="display:flex;align-items:center;gap:7px;margin:0 0 6px;font-size:11.5px;color:#6b6b70">
         <span>raster opacity</span>
         <input id="ropac" type="range" min="10" max="100" value="75" style="flex:1"></div>`);
    sliderShown = true;
  }
  ras.forEach(rasterRow);
  vec.forEach(vectorRow);
});
if(sliderShown)
  document.getElementById('ropac').addEventListener('input', e => {
    const v = e.target.value / 100;
    rasterMade.filter(m => m.def.group !== 'land').forEach(m => m.lyr.setOpacity(v));
  });

document.getElementById('tolv').textContent = DATA.tol_deg;
document.getElementById('precv').textContent = DATA.precision;

// "All on" means the vector layers only: switching on every raster at once
// would just stack them into an unreadable smear.
document.getElementById('allOn').onclick = () => {
  made.forEach(m => {
    if(!map.hasLayer(m.lyr)) m.lyr.addTo(map);
    if(m.box) m.box.checked = true;
  });
  restack();
};
document.getElementById('allOff').onclick = () => {
  made.forEach(m => { map.removeLayer(m.lyr); if(m.box) m.box.checked = false; });
  rasterMade.forEach(m => { map.removeLayer(m.lyr); if(m.box) m.box.checked = false; });
};
// A layer whose `group` matches no section would be on the map but missing
// from the list — say so rather than let it hide.
const orphans = [...made, ...rasterMade].filter(m => !m.box).map(m => m.def.name);
if(orphans.length) console.warn('layers with an unknown group:', orphans);
document.getElementById('reset').onclick = () => map.fitBounds(IDN);
</script></body></html>
"""

if __name__ == "__main__":
    sys.exit(main())
