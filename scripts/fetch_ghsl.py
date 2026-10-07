#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["geopandas>=1", "pyogrio", "shapely>=2"]
# ///
"""
Fetch the multi-epoch GHSL tiles that cover Indonesia.

    uv run --script scripts/fetch_ghsl.py --dry-run
    uv run --script scripts/fetch_ghsl.py --import-from ~/Downloads   # reuse browser downloads
    uv run --script scripts/fetch_ghsl.py                              # fetch everything from JRC

What it fetches
---------------
Four GHSL R2023A products x seven epochs (1990-2020, every 5 years):

    BUILT-S  built-up surface (m2 of roof per cell)   100 m
    BUILT-V  built-up volume  (m3 per cell)           100 m
    POP      residential population                   100 m
    SMOD     degree of urbanisation (class labels)    1 km

1990/1995/2000 are the pre-period predictors and 2005-2020 the outcome window
(proposal 6.2). Which epoch ends the predictor window is still open
(considerations M5).

Why tiles, and which ones
-------------------------
GHSL publishes each product either as one GLOBAL file or as tiles on a grid of
1000 km squares in Mollweide. Indonesia is ~1.5% of the globe, so the global
file is ~98% waste (and the reason the disk once filled up: considerations D10).

The tile list is DERIVED, not typed by hand: every grid tile that intersects
Indonesian land (BIG's Area Daratan polygons), then the full rectangular block
of rows x columns those tiles span. That gives R9-R11 x C28-C33 = 18 tiles.
Only 15 of them actually contain Indonesian land; the other 3 are taken
anyway so that each epoch mosaics into one clean rectangle.

Integrity
---------
Every zip is checked twice: its byte size must equal the server's
Content-Length, and every member must pass the zip CRC test. A browser that
is interrupted leaves a stub .zip next to a .zip.part, and the stub LOOKS like
a download -- 15 of the first batch were exactly that. Downloads go to a .part
file and are renamed only once complete, so this script never leaves one.

A sha256 manifest is written to metadata/manifests/ghsl_tiles.csv, in the same
columns as metadata/file_manifest.csv.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import pathlib
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
LAND = RAW / "big_databatimetri_2017" / "2026-09-12" / "big_area_daratan_land.geojson"
GRID = RAW / "ghsl_tile_grid" / "2026-09-11" / "GHSL_data_54009_shapefile"
MANIFEST = ROOT / "metadata" / "manifests" / "ghsl_tiles.csv"
BATCH = "2026-10-07_tiles"      # retrieval batch folder name (data/raw/<source>/<batch>/)
UA = "indonesia-sez-research/0.1 (academic use)"
BASE = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL"

EPOCHS = [1990, 1995, 2000, 2005, 2010, 2015, 2020]
# product code -> (resolution in metres, version). SMOD is a 1 km product at V2.
PRODUCTS = {"BUILT_S": (100, "1"), "BUILT_V": (100, "1"),
            "POP": (100, "1"), "SMOD": (1000, "2")}


def source_id(product: str) -> str:
    """Folder name under data/raw/, following the repo's <source_id>/<batch>/ layout."""
    return f"ghsl_{product.lower()}_r2023a"


def tile_name(product: str, epoch: int, tile: str) -> str:
    res, ver = PRODUCTS[product]
    return f"GHS_{product}_E{epoch}_GLOBE_R2023A_54009_{res}_V{ver}_0_{tile}.zip"


def tile_url(product: str, epoch: int, tile: str) -> str:
    res, ver = PRODUCTS[product]
    return (f"{BASE}/GHS_{product}_GLOBE_R2023A/GHS_{product}_E{epoch}_GLOBE_R2023A_54009_{res}"
            f"/V{ver}-0/tiles/{tile_name(product, epoch, tile)}")


def derive_tiles() -> list[str]:
    """Tiles intersecting Indonesian land, widened to their bounding row x column block."""
    import geopandas as gpd  # imported here so --help works without the dependency

    grid = gpd.read_file(next(GRID.glob("*.shp")))
    land = gpd.read_file(LAND)
    land = land[land["NEGARA"].str.contains("Indonesia", case=False, na=False)]
    # buffer(0) repairs the one degenerate ring in this layer (considerations D7).
    land = land.set_geometry(land.geometry.buffer(0)).to_crs(grid.crs)
    hit = gpd.sjoin(grid, land[["geometry"]], predicate="intersects")["tile_id"].unique()
    rows = [int(t.split("_")[0][1:]) for t in hit]
    cols = [int(t.split("_")[1][1:]) for t in hit]
    print(f"  {len(hit)} tiles hold Indonesian land; block R{min(rows)}-R{max(rows)} "
          f"x C{min(cols)}-C{max(cols)}")
    return [f"R{r}_C{c}" for r in range(min(rows), max(rows) + 1)
            for c in range(min(cols), max(cols) + 1)]


def remote_size(url: str) -> int | None:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return int(r.headers["Content-Length"])
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(2 ** attempt)
    raise RuntimeError(f"HEAD failed repeatedly: {url}")


def is_valid(path: pathlib.Path, size: int) -> bool:
    """Right size AND every member passes its CRC check."""
    if not path.exists() or path.stat().st_size != size:
        return False
    try:
        with zipfile.ZipFile(path) as z:
            return z.testzip() is None
    except zipfile.BadZipFile:
        return False


def download(url: str, dest: pathlib.Path, size: int, retries: int = 4) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            if is_valid(tmp, size):
                tmp.rename(dest)
                return
            print(f"    ! incomplete or corrupt, retrying ({attempt + 1}/{retries})")
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"    ! {e}, retrying ({attempt + 1}/{retries})")
        time.sleep(2 ** attempt)
    tmp.unlink(missing_ok=True)
    raise RuntimeError(f"could not download {url}")


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--import-from", type=pathlib.Path,
                    help="folder of browser-downloaded tile zips to reuse (copied, not moved)")
    ap.add_argument("--dry-run", action="store_true", help="list what would happen, change nothing")
    args = ap.parse_args()

    tiles = derive_tiles()
    jobs = [(p, e, t) for p in PRODUCTS for e in EPOCHS for t in tiles]
    print(f"  expecting {len(jobs)} files = {len(PRODUCTS)} products x {len(EPOCHS)} epochs "
          f"x {len(tiles)} tiles\n")

    rows, counts = [], {"present": 0, "imported": 0, "fetched": 0}
    for i, (product, epoch, tile) in enumerate(jobs, 1):
        name = tile_name(product, epoch, tile)
        url = tile_url(product, epoch, tile)
        dest = RAW / source_id(product) / BATCH / name
        size = remote_size(url)
        if size is None:
            print(f"  [{i}/{len(jobs)}] NOT ON SERVER: {name}")
            return 1

        if is_valid(dest, size):
            counts["present"] += 1
        elif args.import_from and is_valid(args.import_from / name, size):
            # Browser copy is complete and matches the server byte for byte in size.
            if not args.dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(args.import_from / name, dest)
            counts["imported"] += 1
        else:
            print(f"  [{i}/{len(jobs)}] fetch {name} ({size / 1e6:.1f} MB)")
            if not args.dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                download(url, dest, size)
            counts["fetched"] += 1

        if not args.dry_run:
            rows.append({
                "path": str(dest.relative_to(ROOT)), "source_id": source_id(product),
                "bytes": dest.stat().st_size, "sha256": sha256(dest), "format": "ZIP (GeoTIFF)",
                "spatial_extent": f"GHSL tile {tile}, ESRI:54009",
                "temporal_extent": str(epoch), "rows_or_dimensions": "",
                "validation_status": "verified: size = server Content-Length; zip CRC ok",
                "parent_files": "", "transformation_command": f"GET {url}",
                "retrieved_at": dt.datetime.fromtimestamp(dest.stat().st_mtime, dt.timezone.utc)
                                  .isoformat(timespec="seconds"),
                "http_last_modified": "", "http_etag": ""})

    print(f"\n  already present {counts['present']}, imported {counts['imported']}, "
          f"fetched {counts['fetched']}")
    if args.dry_run:
        return 0

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"  manifest: {MANIFEST.relative_to(ROOT)} ({len(rows)} rows)")

    # Final count per product, so a gap can never pass silently.
    ok = True
    for product in PRODUCTS:
        n = len(list((RAW / source_id(product) / BATCH).glob("*.zip")))
        want = len(EPOCHS) * len(tiles)
        print(f"  {source_id(product):22} {n}/{want}")
        ok &= n == want
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
