#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["rasterio>=1.3", "numpy"]
# ///
"""
Join the 18 GHSL tiles of each product x epoch into one virtual mosaic.

    uv run --script scripts/build_ghsl_mosaics.py

Run after scripts/fetch_ghsl.py. Produces, in data/interim/ghsl/:

    tiles/<product>/E<epoch>/*.tif      the GeoTIFFs, extracted from the raw zips
    GHS_<product>_E<epoch>_..._IDN18.vrt  one mosaic per product x epoch (28)

What a VRT is, and why not one big GeoTIFF
------------------------------------------
A VRT ("virtual raster") is a small XML file that says "this raster is these 18
files, placed side by side". Any GDAL-based tool (rasterio, QGIS, geopandas'
raster friends) opens it as if it were one image. Writing a real merged GeoTIFF
instead would copy every pixel a second time: a 100 m mosaic of 18 tiles is
60,000 x 30,000 cells, and the float64 population layer alone would be ~14 GB
uncompressed. The VRT is a few kB.

Why the tiles are extracted rather than read inside the zip
-----------------------------------------------------------
GDAL can read a .tif inside a .zip (/vsizip/), but a VRT can then only point at
it by ABSOLUTE path -- and absolute paths break the moment the project folder
moves or is cloned on a co-author's machine. Extracted tiles sit next to the
VRT and are referenced relatively. data/raw/ keeps the zips exactly as the
server sent them; data/interim/ is derived and can be rebuilt by this script.

Checks (each one stops the script rather than warn)
----------------------------------------------------
* All 18 tiles of a mosaic share CRS, pixel size, data type and nodata.
  Placing tiles side by side is only valid if they are on the same grid.
* SMOD class codes are a subset of the documented GHSL set (considerations D13).
"""

from __future__ import annotations

import pathlib
import sys
import zipfile
from xml.sax.saxutils import escape

import numpy as np
import rasterio

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "interim" / "ghsl"
BATCH = "2026-10-07_tiles"
PRODUCTS = ["BUILT_S", "BUILT_V", "POP", "SMOD"]
EPOCHS = [1990, 1995, 2000, 2005, 2010, 2015, 2020]
SMOD_CODES = {10, 11, 12, 13, 21, 22, 23, 30}

# rasterio dtype name -> the name GDAL writes in a VRT
GDAL_TYPE = {"uint8": "Byte", "uint16": "UInt16", "int16": "Int16", "uint32": "UInt32",
             "int32": "Int32", "float32": "Float32", "float64": "Float64"}


def extract(product: str, epoch: int) -> list[pathlib.Path]:
    """Extract the .tif of every tile zip for one product x epoch (skips if present)."""
    zips = sorted((RAW / f"ghsl_{product.lower()}_r2023a" / BATCH).glob(f"GHS_{product}_E{epoch}_*.zip"))
    if len(zips) != 18:
        raise SystemExit(f"{product} {epoch}: {len(zips)} zips, expected 18 -- run fetch_ghsl.py")
    dest = OUT / "tiles" / product / f"E{epoch}"
    dest.mkdir(parents=True, exist_ok=True)
    tifs = []
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            member = next(n for n in zf.namelist() if n.endswith(".tif"))
            target = dest / pathlib.Path(member).name
            if not target.exists() or target.stat().st_size != zf.getinfo(member).file_size:
                with zf.open(member) as src, open(target, "wb") as out:
                    while block := src.read(1 << 20):
                        out.write(block)
            tifs.append(target)
    return tifs


def write_vrt(tifs: list[pathlib.Path], vrt: pathlib.Path) -> None:
    """Write a mosaic VRT. Every tile must be on the same grid."""
    meta = []
    for t in tifs:
        with rasterio.open(t) as s:
            meta.append((t, s.crs, s.res, s.dtypes[0], s.nodata, s.bounds, s.width, s.height))

    first = meta[0]
    for m in meta[1:]:
        if (m[1], m[2], m[3], m[4]) != (first[1], first[2], first[3], first[4]):
            raise SystemExit(f"{m[0].name} is not on the same grid as {first[0].name}")

    res = first[2][0]
    left = min(m[5].left for m in meta)
    top = max(m[5].top for m in meta)
    right = max(m[5].right for m in meta)
    bottom = min(m[5].bottom for m in meta)
    W, H = round((right - left) / res), round((top - bottom) / res)

    sources = []
    for t, _, _, _, _, b, w, h in meta:
        xoff, yoff = round((b.left - left) / res), round((top - b.top) / res)
        rel = t.relative_to(vrt.parent).as_posix()
        sources.append(
            f'    <SimpleSource>\n'
            f'      <SourceFilename relativeToVRT="1">{escape(rel)}</SourceFilename>\n'
            f'      <SourceBand>1</SourceBand>\n'
            f'      <SrcRect xOff="0" yOff="0" xSize="{w}" ySize="{h}"/>\n'
            f'      <DstRect xOff="{xoff}" yOff="{yoff}" xSize="{w}" ySize="{h}"/>\n'
            f'    </SimpleSource>')
    # Written exactly: BUILT-V's nodata is 4294967295 (the uint32 maximum), and
    # a rounded "4.29497e+09" no longer matches it, so every sea cell would turn
    # into a real value of 4.3 billion cubic metres.
    nd = first[4]
    if nd is not None and float(nd).is_integer():
        nd = int(nd)
    nodata = f"<NoDataValue>{nd}</NoDataValue>" if nd is not None else ""
    vrt.write_text(
        f'<VRTDataset rasterXSize="{W}" rasterYSize="{H}">\n'
        f'  <SRS>{escape(first[1].to_wkt())}</SRS>\n'
        f'  <GeoTransform>{left:.1f}, {res:g}, 0, {top:.1f}, 0, {-res:g}</GeoTransform>\n'
        f'  <VRTRasterBand dataType="{GDAL_TYPE[first[3]]}" band="1">\n'
        f'    {nodata}\n' + "\n".join(sources) + '\n  </VRTRasterBand>\n</VRTDataset>\n')


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for product in PRODUCTS:
        for epoch in EPOCHS:
            tifs = extract(product, epoch)
            # Name follows the GHSL convention, with IDN18 marking "our 18-tile block".
            stem = tifs[0].name.rsplit("_R", 1)[0]
            vrt = OUT / f"{stem}_IDN18.vrt"
            write_vrt(tifs, vrt)

            with rasterio.open(vrt) as s:
                line = f"  {vrt.name:<55} {s.width}x{s.height} {s.dtypes[0]:<8} nodata {s.nodata:g}"
                if product == "SMOD":
                    # 1 km: small enough to read whole and check every code.
                    codes = set(np.unique(s.read(1)).tolist()) - {s.nodata}
                    if not codes <= SMOD_CODES:
                        raise SystemExit(f"unexpected SMOD codes {sorted(codes - SMOD_CODES)}")
                    line += f"  codes {sorted(codes)}"
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
