#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Fetch Copernicus DEM tiles covering Indonesian land.

    uv run --script scripts/fetch_terrain.py --dry-run      # count and size first
    uv run --script scripts/fetch_terrain.py                # GLO-90 (default)
    uv run --script scripts/fetch_terrain.py --res 30       # GLO-30, ~9x bigger

Why Copernicus and not BIG or SRTM
-----------------------------------
BIG publishes no national DEM through its REST services, and the RBI sheet index
records BIG's own source as "SRTM 30m dan ASTER DEM" — the national product IS
the global product, reprocessed (considerations D6). Copernicus DEM is on AWS
Open Data with no credentials and no login, which SRTM via USGS/Earthdata is not.

Which tiles
-----------
Not a bounding box. A box around Indonesia is 782 one-degree cells and mostly
sea. Instead the tile list is derived from the land polygons already on disk
(`Area Daratan`), by two tests that catch different things:

  * a cell holding any polygon VERTEX   -> coastlines and small islands
  * a cell whose CENTRE is inside land  -> the interior of big islands, which
                                           has no coastline vertices in it at all

Vertices alone would have missed central Borneo, Sumatra and Papua entirely —
large, mountainous, and exactly where a ruggedness layer matters most.

A missing tile is not an error: Copernicus publishes no tile for a cell with no
land, so a 404 is an answer. They are counted and listed, not retried.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
LAND = RAW / "big_databatimetri_2017" / "2026-09-12" / "big_area_daratan_land.geojson"
UA = "indonesia-sez-research/0.1 (academic use)"

# Copernicus DEM on AWS Open Data. The number in the key is the grid spacing in
# arc-seconds: 10 for GLO-30, 30 for GLO-90.
BUCKET = {30: ("copernicus-dem-30m", 10), 90: ("copernicus-dem-90m", 30)}


def rings_of(geom):
    """Yield every exterior ring in a Polygon/MultiPolygon."""
    t, c = geom.get("type"), geom.get("coordinates")
    if t == "Polygon":
        if c:
            yield c[0]
    elif t == "MultiPolygon":
        for poly in c or []:
            if poly:
                yield poly[0]


def point_in_ring(x, y, ring) -> bool:
    """Ray casting. Counts crossings of a horizontal ray to the east."""
    inside = False
    n = len(ring)
    for i in range(n - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        if (y1 > y) != (y2 > y):
            xc = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xc > x:
                inside = not inside
    return inside


def land_cells() -> set[tuple[int, int]]:
    """The set of (lon0, lat0) one-degree cells containing Indonesian land."""
    if not LAND.exists():
        sys.exit(f"missing {LAND} — run scripts/fetch_big.py for the land layer first")
    fc = json.loads(LAND.read_text())
    feats = fc["features"]

    cells: set[tuple[int, int]] = set()
    boxes = []                      # (minx, miny, maxx, maxy, ring) for the centre test

    for f in feats:
        for ring in rings_of(f.get("geometry") or {}):
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            for p in ring:                       # test 1: vertices
                cells.add((int(p[0] // 1), int(p[1] // 1)))
            boxes.append((min(xs), min(ys), max(xs), max(ys), ring))

    vertex_only = len(cells)

    # test 2: cell centres inside land, for interiors with no coastline in them
    lon0 = min(int(b[0] // 1) for b in boxes)
    lon1 = max(int(b[2] // 1) for b in boxes)
    lat0 = min(int(b[1] // 1) for b in boxes)
    lat1 = max(int(b[3] // 1) for b in boxes)
    for lon in range(lon0, lon1 + 1):
        for lat in range(lat0, lat1 + 1):
            if (lon, lat) in cells:
                continue
            cx, cy = lon + .5, lat + .5
            for minx, miny, maxx, maxy, ring in boxes:
                if minx <= cx <= maxx and miny <= cy <= maxy and point_in_ring(cx, cy, ring):
                    cells.add((lon, lat))
                    break

    interior = len(cells) - vertex_only

    # Fill cells that are enclosed on all four sides by land cells. In an
    # archipelago these are interior SEAS — Flores, Banda, Molucca — not holes in
    # the land, so nothing is missing from them. They are included anyway because
    # ruggedness is computed with a moving window, and a missing tile inside the
    # study area puts a nodata seam through the middle of that window rather than
    # at the coast where it belongs. They cost a few MB each.
    enclosed = set()
    for lon, lat in list(cells):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            c = (lon + dx, lat + dy)
            if c in cells or c in enclosed:
                continue
            if all((c[0] + ex, c[1] + ey) in cells
                   for ex, ey in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                enclosed.add(c)
    cells |= enclosed

    print(f"  land cells: {len(cells)}  ({vertex_only} from vertices, "
          f"{interior} interior-only, {len(enclosed)} enclosed sea)")
    return cells


def tile_key(lon: int, lat: int, grid: int) -> str:
    ns = f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}"
    ew = f"{'E' if lon >= 0 else 'W'}{abs(lon):03d}"
    return f"Copernicus_DSM_COG_{grid}_{ns}_00_{ew}_00_DEM"


def head(url: str, timeout=30) -> int | None:
    """Content-Length, or None if the tile does not exist."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return int(r.headers.get("Content-Length") or 0)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return None
        raise


def download(url: str, dest: pathlib.Path, retries=4) -> int:
    """Download to a .part file and rename on success, so an interrupted run
    never leaves a truncated .tif that looks complete."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as fh:
                expect = int(r.headers.get("Content-Length") or 0)
                got = 0
                while chunk := r.read(1 << 20):
                    fh.write(chunk)
                    got += len(chunk)
            if expect and got != expect:
                raise OSError(f"short read {got} of {expect}")
            tmp.rename(dest)
            return got
        except Exception as exc:
            if tmp.exists():
                tmp.unlink()
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, choices=(30, 90), default=90,
                    help="GLO-30 or GLO-90 (default 90)")
    ap.add_argument("--dry-run", action="store_true",
                    help="list tiles and total size, download nothing")
    ap.add_argument("--limit", type=int, default=None, help="stop after N tiles")
    args = ap.parse_args()

    bucket, grid = BUCKET[args.res]
    # Repo layout: data/raw/<source_id>/<retrieval date>/. A re-run on another
    # day therefore lands in a new folder rather than mixing two retrievals.
    dest_dir = RAW / f"copernicus_dem_glo{args.res}" / time.strftime("%Y-%m-%d")
    if not args.dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"Copernicus DEM GLO-{args.res}  (bucket {bucket}, grid code {grid})")
    cells = sorted(land_cells())

    free = os.statvfs(RAW).f_bavail * os.statvfs(RAW).f_frsize
    print(f"  free disk: {free/1e9:.1f} GB\n")

    have, missing, todo, bytes_todo = 0, [], [], 0
    for lon, lat in cells:
        key = tile_key(lon, lat, grid)
        dest = dest_dir / f"{key}.tif"
        if dest.exists() and dest.stat().st_size > 0:
            have += 1
            continue
        url = f"https://{bucket}.s3.amazonaws.com/{key}/{key}.tif"
        size = head(url)
        if size is None:
            missing.append(key)
            continue
        todo.append((key, url, dest, size))
        bytes_todo += size

    print(f"  already on disk : {have}")
    print(f"  no tile published: {len(missing)}  (cells with no land in Copernicus)")
    print(f"  to download     : {len(todo)}  =  {bytes_todo/1e9:.2f} GB")

    if bytes_todo > free * 0.9:
        sys.exit(f"\nREFUSING: {bytes_todo/1e9:.1f} GB needed, {free/1e9:.1f} GB free.")

    if args.dry_run:
        print("\n  dry run — nothing downloaded")
        return 0

    got = 0
    for i, (key, url, dest, size) in enumerate(todo[:args.limit], 1):
        n = download(url, dest)
        got += n
        print(f"  [{i:>4}/{len(todo)}] {key}  {n/1e6:6.1f} MB  "
              f"({got/1e9:.2f} GB)", flush=True)

    print(f"\n  {len(todo)} tiles, {got/1e9:.2f} GB -> {dest_dir}")
    (dest_dir / "_no_tile_published.txt").write_text("\n".join(missing))
    print(f"  {len(missing)} cells have no published tile; listed in "
          f"{dest_dir.name}/_no_tile_published.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
