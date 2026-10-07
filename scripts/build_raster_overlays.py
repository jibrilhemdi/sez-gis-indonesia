#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["rasterio>=1.3", "numpy", "pillow", "pyyaml"]
# ///
"""
Turn the raster layers listed in config/map_layers.yaml into PNG overlays.

    uv run --script scripts/build_raster_overlays.py

Slow (a few minutes): it reads every raster. Re-run only when a raster or its
entry changes; scripts/build_map.py then embeds the PNGs into the page.

Why this needs care rather than just "read the tif"
---------------------------------------------------
1. THE SOURCES ARE LARGE. One 100 m GHSL mosaic is 60,000 x 30,000 cells.
   Nothing here reads it whole: we compute the window covering Indonesia, then
   ask for a DECIMATED read at a few times the output size.

2. MOST OF THEM ARE IN MOLLWEIDE, NOT LON/LAT. Leaflet places an image overlay
   by stretching it linearly between two corners in the map's own projection
   (Web Mercator). Handing it a Mollweide image — or even a plate-carree one —
   puts the coastlines in the wrong place. So each raster is warped to EPSG:3857
   on a grid whose extent is exactly the overlay bounds. Then the stretch is
   exact rather than approximately right.

3. CATEGORICAL RASTERS MUST NOT BE AVERAGED. Resampling SMOD's class codes with
   `average` would produce class 16.5 — a number that means nothing. Categorical
   layers use nearest-neighbour; continuous ones use average.

4. A TIME SERIES SHARES ONE COLOUR SCALE. The stretch for a series is computed
   from all its epochs pooled, then applied to each. Stretching every epoch on
   its own would map 1990's maximum and 2020's maximum to the same dark colour,
   and the map would show no growth at all.

5. THE PNGs ARE PALETTE IMAGES (8-bit, 256 colours), not full RGBA. The colour
   ramps only have 256 entries anyway, so nothing is lost, and the files are
   several times smaller — which matters because the page embeds all of them
   and has to stay under GitHub's 50 MB warning size.

What this is not
----------------
A display copy, like the vector map. Values are binned to colours and the grid
is resampled to screen resolution. Read it to see WHERE things are, never to
measure HOW MUCH.
"""

from __future__ import annotations

import json
import pathlib
import sys
import warnings

import numpy as np
import rasterio
import yaml
from rasterio.warp import calculate_default_transform, reproject, transform_bounds
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from rasterio.features import rasterize
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "map_layers.yaml"
OUT = ROOT / "outputs" / "map" / "rasters"

# The study area. Everything is clipped to this — the sources are global and
# Indonesia is the only part that matters.
IDN = (94.8, -11.3, 141.3, 6.4)          # west, south, east, north (EPSG:4326)
WIDTH = 2000                              # output px; height follows the aspect


# ------------------------------------------------------------------ colour ---

def ramp(stops):
    """Build a 256-entry RGB lookup table from (position, (r,g,b)) stops."""
    lut = np.zeros((256, 3), dtype=np.uint8)
    xs = [int(p * 255) for p, _ in stops]
    for i in range(len(stops) - 1):
        a, b = xs[i], xs[i + 1]
        ca, cb = np.array(stops[i][1], float), np.array(stops[i + 1][1], float)
        n = max(b - a, 1)
        for k in range(n + 1):
            lut[min(a + k, 255)] = ca + (cb - ca) * (k / n)
    lut[xs[-1]:] = stops[-1][1]
    return lut


RAMPS = {
    "built":  ramp([(0, (255, 247, 236)), (.35, (253, 190, 133)),
                    (.7, (217, 95, 14)), (1, (127, 39, 4))]),
    "pop":    ramp([(0, (247, 252, 245)), (.35, (161, 217, 155)),
                    (.7, (49, 144, 89)), (1, (0, 68, 27))]),
    "volume": ramp([(0, (247, 244, 249)), (.4, (191, 155, 205)),
                    (.75, (140, 66, 157)), (1, (73, 0, 106))]),
}

# GHSL degree-of-urbanisation classes. Codes are documented, not guessed:
# 30 urban centre; 23/22/21 dense town, semi-dense town, suburban;
# 13/12/11 village, dispersed rural, mostly uninhabited; 10 water.
SMOD_COLORS = {
    30: (178, 24, 43), 23: (227, 74, 51), 22: (253, 141, 60), 21: (254, 196, 79),
    13: (199, 233, 180), 12: (161, 217, 155), 11: (229, 245, 224), 10: (0, 0, 0, 0),
}
SMOD_LABELS = {
    30: "Urban centre", 23: "Dense town", 22: "Semi-dense town", 21: "Suburban",
    13: "Village", 12: "Dispersed rural", 11: "Mostly uninhabited", 10: "Water",
}

# WorldPop's level-1 grid does NOT use the SMOD codes — it uses 1/2/3. Assuming
# otherwise rendered it completely empty, silently: every pixel failed to match a
# class, so nothing was drawn and the PNG was a valid, blank image. A categorical
# layer whose codes you have not checked is a layer you cannot draw.
DUG_L1_COLORS = {3: (178, 24, 43), 2: (254, 196, 79), 1: (199, 233, 180)}
DUG_L1_LABELS = {3: "City", 2: "Town / semi-dense", 1: "Rural"}

CLASS_TABLES = {
    "classes":    (SMOD_COLORS, SMOD_LABELS, (30, 23, 22, 21, 13, 12, 11)),
    "classes_l1": (DUG_L1_COLORS, DUG_L1_LABELS, (3, 2, 1)),
}


# ------------------------------------------------------------------- build ---

def block_nanmean(a: np.ndarray, fy: int, fx: int) -> np.ndarray:
    """Average a by integer factors, ignoring NaN."""
    h = (a.shape[0] // fy) * fy
    w = (a.shape[1] // fx) * fx
    a = a[:h, :w].reshape(h // fy, fy, w // fx, fx)
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        # An all-NaN block is ocean, which is expected everywhere in this study
        # area and is not worth a warning per occurrence.
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(a, axis=(1, 3))


def read_indonesia(src, width, height, categorical, vmax=None):
    """Decimated read of the Indonesia window, warped to EPSG:3857.

    Returns (array, dst_bounds_3857). The decimated read is what keeps a 61 GiB
    file cheap: GDAL serves it from the overview pyramid.
    """
    dst_bounds = transform_bounds("EPSG:4326", "EPSG:3857", *IDN, densify_pts=21)

    # Window on the source, in the source's own CRS.
    src_bounds = transform_bounds("EPSG:4326", src.crs, *IDN, densify_pts=21)
    win = from_bounds(*src_bounds, transform=src.transform).round_offsets().round_lengths()
    # Clamp to the file, in case the study area runs off its edge.
    win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))

    # ALWAYS read nearest. A decimated `average` read mixes nodata into real
    # values: GHS-BUILT-S is uint8 with nodata 255 and a physical maximum of 100
    # (m2 of roof in a 10 m cell), and averaging ocean-255 against land produced
    # impossible values of 101-254 which then rendered as built-up across half
    # the country. Averaging happens below, in numpy, AFTER nodata is masked.
    over = 2 if categorical else 4
    out_h = min(int(height * over), int(win.height)) or 1
    out_w = min(int(width * over), int(win.width)) or 1
    arr = src.read(1, window=win, out_shape=(out_h, out_w),
                   resampling=Resampling.nearest, boundless=False)

    src_t = src.window_transform(win) * rasterio.Affine.scale(
        win.width / arr.shape[1], win.height / arr.shape[0])

    if categorical:
        dst = np.zeros((height, width), dtype=arr.dtype)
        dst_t = rasterio.transform.from_bounds(*dst_bounds, width, height)
        reproject(source=arr, destination=dst,
                  src_transform=src_t, src_crs=src.crs,
                  dst_transform=dst_t, dst_crs="EPSG:3857",
                  resampling=Resampling.nearest,
                  src_nodata=src.nodata, dst_nodata=0)
        return dst, dst_bounds

    f = arr.astype("float32")
    if src.nodata is not None:
        f[f == np.float32(src.nodata)] = np.nan
    if vmax is not None:
        # Anything above the layer's physical maximum is nodata or corruption,
        # whatever the header claims.
        f[f > vmax] = np.nan
    f[f < 0] = np.nan

    k = 4
    if f.shape[0] >= k * 2 and f.shape[1] >= k * 2:
        f = block_nanmean(f, k, k)
        src_t = src_t * rasterio.Affine.scale(k, k)

    dst = np.full((height, width), np.nan, dtype="float32")
    dst_t = rasterio.transform.from_bounds(*dst_bounds, width, height)
    reproject(source=f, destination=dst,
              src_transform=src_t, src_crs=src.crs,
              dst_transform=dst_t, dst_crs="EPSG:3857",
              resampling=Resampling.average,
              src_nodata=np.nan, dst_nodata=np.nan)
    return dst, dst_bounds


def percentile_stretch(arrays):
    """2nd-99.5th percentile of the positive values, pooled over all arrays.

    Percentiles rather than min-max: these distributions are extremely
    long-tailed, so a min-max stretch renders everything black except a
    handful of city cells.
    """
    vals = np.concatenate([a[np.isfinite(a) & (a > 0)].ravel() for a in arrays])
    if not vals.size:
        return 0.0, 1.0
    lo, hi = float(np.percentile(vals, 2)), float(np.percentile(vals, 99.5))
    return lo, (hi if hi > lo else lo + 1)


def colourise(arr, mode, nodata, stretch=None):
    """Map values to RGBA. Zero / nodata becomes transparent.

    `stretch` = (lo, hi) fixes the colour scale; a time series passes the one
    computed over all its epochs. Without it, the scale comes from this array.
    """
    h, w = arr.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    a = arr.astype("float64")   # continuous arrays already carry NaN for nodata

    if mode.startswith("classes"):
        colors, labels, order = CLASS_TABLES[mode]
        drawn = 0
        for code in order:
            m = arr == code
            drawn += int(m.sum())
            rgba[m, :3] = colors[code][:3]
            rgba[m, 3] = 205
        if drawn == 0:
            # Loudly, rather than shipping a blank PNG that looks like "no data here".
            present = sorted({int(v) for v in np.unique(arr)})[:15]
            raise ValueError(
                f"no pixel matched any class in {mode}; values present are {present}. "
                "The class table is wrong for this raster.")
        return rgba, {"kind": "classes",
                      "classes": [{"code": c, "label": labels[c],
                                   "color": "#%02x%02x%02x" % colors[c][:3]}
                                  for c in order]}

    valid = np.isfinite(a) & (a > 0)
    if not valid.any():
        return rgba, {"kind": "empty"}

    lo, hi = stretch if stretch else percentile_stretch([a])
    # Log scaling, because built-up area and population both span orders of
    # magnitude; a linear ramp shows Jakarta and nothing else.
    norm = np.zeros_like(a)
    norm[valid] = (np.log1p(np.clip(a[valid], lo, hi) - lo) / np.log1p(hi - lo))
    idx = np.clip((norm * 255), 0, 255).astype(np.uint8)

    lut = RAMPS[mode]
    rgba[..., :3] = lut[idx]
    rgba[..., 3] = np.where(valid, 200, 0).astype(np.uint8)
    return rgba, {"kind": "continuous", "p2": lo, "p99_5": hi,
                  "ramp": ["#%02x%02x%02x" % tuple(lut[i]) for i in (0, 64, 128, 192, 255)]}


# --------------------------------------------------------------- terrain ---

def land_mask(src, width, height, dst_bounds):
    """Rasterise BIG's land polygons onto the output grid.

    Applies considerations D9: the layer encodes inland water two ways, and the
    496 polygons named TOPONIM=DANAU are standalone LAKES. Burn every polygon as
    land and those lakes become dry ground — so they are excluded here, which is
    the same rule the analysis land mask will need.
    """
    if src is None or not src.exists():
        print("    no land polygons — terrain will include the sea")
        return None
    fc = json.loads(src.read_text())

    def to_3857(coords):
        if coords and isinstance(coords[0][0], (int, float)):
            xs, ys = zip(*[(c[0], c[1]) for c in coords])
            X, Y = rasterio.warp.transform("EPSG:4326", "EPSG:3857", list(xs), list(ys))
            return list(zip(X, Y))
        return [to_3857(c) for c in coords]

    shapes, lakes = [], 0
    for f in fc["features"]:
        if (f["properties"].get("TOPONIM") or "").upper() == "DANAU":
            lakes += 1
            continue
        g = f.get("geometry") or {}
        if g.get("type") in ("Polygon", "MultiPolygon") and g.get("coordinates"):
            shapes.append({"type": g["type"], "coordinates": to_3857(g["coordinates"])})

    dst_t = rasterio.transform.from_bounds(*dst_bounds, width, height)
    m = rasterize(((s, 1) for s in shapes), out_shape=(height, width),
                  transform=dst_t, fill=0, dtype="uint8", all_touched=True)
    print(f"    land mask: {len(shapes)} polygons burned, {lakes} DANAU lakes "
          f"excluded, {m.mean()*100:.1f}% of frame is land")
    return m.astype(bool)

def build_terrain(tile_dir, land, width, height, dst_bounds):
    """Mosaic the 467 Copernicus tiles into one shaded-relief overlay.

    Not rasterio.merge: mosaicking 467 tiles of 1200x1200 float32 in memory is
    ~3 GB for a picture 4000 px wide. Each tile is instead reprojected straight
    into its own small window of the output grid and composited there, so peak
    memory is one tile plus the output.
    """
    tiles = sorted(tile_dir.rglob("*.tif"))
    if not tiles:
        return None
    print(f"  mosaicking {len(tiles)} DEM tiles ...", flush=True)

    dem = np.full((height, width), np.nan, dtype="float32")
    dst_t = rasterio.transform.from_bounds(*dst_bounds, width, height)
    used = 0
    skipped: list[str] = []

    for i, tp in enumerate(tiles):
        with rasterio.open(tp) as src:
            tb = transform_bounds(src.crs, "EPSG:3857", *src.bounds, densify_pts=21)
            win = from_bounds(*tb, transform=dst_t).round_offsets().round_lengths()
            # Clip by hand rather than Window.intersection, which RAISES on an
            # empty result. Some tiles lie wholly outside the frame: the land
            # polygons reach 7.13N in Malaysia while the map stops at 6.4N, so
            # a handful of northern tiles have no overlap at all. That is
            # expected, not an error.
            c0 = max(0, int(win.col_off)); r0 = max(0, int(win.row_off))
            c1 = min(width, int(win.col_off + win.width))
            r1 = min(height, int(win.row_off + win.height))
            if c1 <= c0 or r1 <= r0:
                skipped.append(tp.name)
                continue
            win = rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0)
            sub = np.full((int(win.height), int(win.width)), np.nan, dtype="float32")
            reproject(source=rasterio.band(src, 1), destination=sub,
                      src_transform=src.transform, src_crs=src.crs,
                      dst_transform=rasterio.windows.transform(win, dst_t),
                      dst_crs="EPSG:3857", resampling=Resampling.average,
                      src_nodata=src.nodata, dst_nodata=np.nan)
        r0, c0 = int(win.row_off), int(win.col_off)
        patch = dem[r0:r0 + sub.shape[0], c0:c0 + sub.shape[1]]
        m = np.isfinite(sub)
        patch[m] = sub[m]
        used += 1
        if (i + 1) % 100 == 0:
            print(f"    {i+1}/{len(tiles)}", flush=True)

    # Copernicus fills the sea with 0 m rather than nodata, so the raw mosaic
    # covers 55% of the frame when Indonesia is about 17% land. Zero is also a
    # perfectly good elevation for a coastal plain, so the sea cannot be removed
    # by value — it needs a land mask.
    mask = land_mask(land, width, height, dst_bounds)
    if mask is not None:
        dem[~mask] = np.nan
    dem[dem < -50] = np.nan
    print(f"    {used} tiles placed, {len(skipped)} outside the frame, "
          f"{np.isfinite(dem).mean()*100:.1f}% of frame")
    return dem


def hillshade(dem, dst_bounds, width, height, az=315.0, alt=45.0):
    """Standard hillshade. Cell size is taken from the Mercator grid, which
    stretches with latitude — over Indonesia (11S-6N) that is at most a few per
    cent, and it changes shading intensity slightly, never position."""
    res_x = (dst_bounds[2] - dst_bounds[0]) / width
    res_y = (dst_bounds[3] - dst_bounds[1]) / height
    z = np.where(np.isfinite(dem), dem, 0.0)
    dy, dx = np.gradient(z, res_y, res_x)
    slope = np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)
    a, z0 = np.radians(az), np.radians(alt)
    hs = (np.sin(z0) * np.cos(slope)
          + np.cos(z0) * np.sin(slope) * np.cos(a - aspect))
    return np.clip(hs, 0, 1)


ELEV_RAMP = ramp([(0, (186, 214, 176)), (.18, (233, 231, 188)),
                  (.42, (206, 176, 120)), (.68, (150, 116, 82)),
                  (.86, (176, 168, 160)), (1, (250, 250, 252))])


def colourise_terrain(dem, dst_bounds, width, height):
    valid = np.isfinite(dem)
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    if not valid.any():
        return rgba, {"kind": "empty"}

    v = dem[valid]
    hi = float(np.percentile(v, 99.5))
    hi = max(hi, 100.0)
    norm = np.clip(np.where(valid, dem, 0) / hi, 0, 1)
    idx = (norm * 255).astype(np.uint8)
    base = ELEV_RAMP[idx].astype("float32")

    hs = hillshade(dem, dst_bounds, width, height)
    # Multiply the elevation tint by relief shading, kept off pure black so the
    # colour still reads in deep shadow.
    shade = (0.45 + 0.55 * hs)[..., None]
    rgba[..., :3] = np.clip(base * shade, 0, 255).astype(np.uint8)
    rgba[..., 3] = np.where(valid, 225, 0).astype(np.uint8)
    return rgba, {"kind": "continuous", "p2": 0.0, "p99_5": hi,
                  "ramp": ["#%02x%02x%02x" % tuple(ELEV_RAMP[i])
                           for i in (0, 64, 128, 192, 255)]}


def save_png(rgba, path, palette=True):
    """Write an overlay. Palette mode (8-bit) unless the image needs more than
    256 colours — terrain does, because hillshade multiplies every tint."""
    img = Image.fromarray(rgba, "RGBA")
    if palette:
        img = img.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
    img.save(path, optimize=True)


def render(path, mode, vmax, width, height):
    """Read one raster for display. Returns (array, bounds_3857, source info)."""
    with rasterio.open(path) as src:
        arr, bounds = read_indonesia(src, width, height, mode.startswith("classes"), vmax)
        info = {"crs": str(src.crs), "src_res": abs(src.transform.a),
                "nodata": None if src.nodata is None else float(src.nodata)}
    return arr, bounds, info


def latlon_bounds(bounds_3857):
    """Leaflet places overlays by [[south, west], [north, east]] in lat/lon."""
    w, s, e, n = transform_bounds("EPSG:3857", "EPSG:4326", *bounds_3857, densify_pts=21)
    return [[s, w], [n, e]]


def main() -> int:
    cfg = yaml.safe_load(CONFIG.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    b = transform_bounds("EPSG:4326", "EPSG:3857", *IDN, densify_pts=21)
    # Height from the Mercator extent, not the lon/lat one, or the image is squashed.
    height = max(1, int(WIDTH * (b[3] - b[1]) / (b[2] - b[0])))
    print(f"Output grid {WIDTH} x {height} px, EPSG:3857, clipped to Indonesia\n")

    # The land polygons double as the sea mask for terrain.
    land = next((ROOT / v["path"] for v in cfg.get("vectors", []) if v.get("ground")), None)

    manifest = []
    for spec in cfg.get("rasters", []):
        name, mode, group = spec["name"], spec["mode"], spec["group"]
        entry = {"name": name, "group": group, "note": spec.get("note", "")}

        # --- terrain: a folder of DEM tiles, rendered at twice the width ---
        if mode == "terrain":
            tile_dir = ROOT / spec["path"]
            tw, th = WIDTH * 2, height * 2
            dem = build_terrain(tile_dir, land, tw, th, b) if tile_dir.exists() else None
            if dem is None:
                print(f"  MISSING  {spec['path']} — skipped"); continue
            rgba, legend = colourise_terrain(dem, b, tw, th)
            png = OUT / "terrain_relief.png"
            save_png(rgba, png, palette=False)
            entry.update(file=f"rasters/{png.name}", bounds=latlon_bounds(b), legend=legend,
                         crs="EPSG:4326 tiles", src_res=0.000833333, nodata=None,
                         coverage=round(float((rgba[..., 3] > 0).mean()), 4))
            manifest.append(entry)
            print(f"  {name:<46} {png.stat().st_size/1e3:>6.0f} kB  ({tw}x{th})")
            continue

        # --- a single raster, or a time series with {epoch} in its path ---
        epochs = spec.get("epochs") or [None]
        paths = [ROOT / spec["path"].format(epoch=e) for e in epochs]
        missing = [p for p in paths if not p.exists()]
        if missing:
            print(f"  MISSING  {missing[0].relative_to(ROOT)} — '{name}' skipped"); continue

        arrays = []
        for e, p in zip(epochs, paths):
            arr, bounds, info = render(p, mode, spec.get("vmax"), WIDTH, height)
            arrays.append(arr)
            print(f"    read {p.name}", flush=True)
        # ONE stretch for the whole series, so the colours are comparable across epochs.
        stretch = None if mode.startswith("classes") else percentile_stretch(arrays)

        files, cover = [], 0.0
        for e, arr, p in zip(epochs, arrays, paths):
            rgba, legend = colourise(arr, mode, info["nodata"], stretch)
            png = OUT / f"{p.stem}.png"
            save_png(rgba, png)
            files.append({"epoch": e, "file": f"rasters/{png.name}"})
            cover = max(cover, float((rgba[..., 3] > 0).mean()))
        if spec.get("epochs"):
            entry["series"] = files
        entry.update(file=files[-1]["file"], bounds=latlon_bounds(bounds), legend=legend,
                     coverage=round(cover, 4), **info)
        manifest.append(entry)
        size = sum((OUT / pathlib.Path(f["file"]).name).stat().st_size for f in files)
        print(f"  {name:<46} {size/1e3:>6.0f} kB  {len(files)} image(s)  "
              f"{cover*100:5.1f}% of frame  ({info['crs']}, res {info['src_res']:g})")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"\n  {len(manifest)} overlays -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
