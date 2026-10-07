#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Download a layer from a Badan Informasi Geospasial (BIG) ArcGIS REST service.

    uv run --script scripts/fetch_big.py \
        --service PTRA/Atlas_Transportasi_Darat --layer 1 \
        --out data/raw/big_atlas_transportasi_darat/2026-09-12/big_transportasi_darat.geojson

An ArcGIS MapServer is an API, not a file download: you ask a layer's /query
endpoint for features and it hands back at most `maxRecordCount` of them per
request (1000 on BIG's servers). Getting all 136,810 road features therefore
means 137 requests, and the whole difficulty of this script is making sure that
"137 requests succeeded" actually means "we have all 136,810 features".

Three things this script does that a hand-written loop usually gets wrong
-------------------------------------------------------------------------

1. IT ORDERS THE RESULTS. Paging with `resultOffset` means "skip the first N
   rows", which is only meaningful if the rows come back in a stable order.
   Without `orderByFields` the server may return them in any order it likes,
   and different orders between requests silently duplicate some features and
   skip others. Every page here is ordered by OBJECTID.

2. IT KNOWS THE ANSWER BEFORE IT STARTS. It asks `returnCountOnly=true` first,
   so there is a number to check the download against. A loop that stops when a
   page comes back short and reports success has verified nothing: a truncated
   road network still loads, still routes, and produces a market-access surface
   that is quietly wrong. A quality gate needs a denominator.

3. IT REFUSES RATHER THAN GUESSES. If the feature count does not match, or any
   OBJECTID arrives twice, it exits non-zero and says so instead of writing a
   plausible-looking file. The worst failure is the one that looks like success.

Everything is stdlib, so it runs with no environment to set up.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://geoservices.big.go.id/gis/rest/services"

# Geometry-shaping defaults. These matter far more than anything else here: BIG
# returns 1:250,000 geometry at full vertex density with Z and M values, which for
# one page of 1000 river features is 43 MB and 53 seconds. Measured, same page:
#
#   baseline (Z+M, 14 decimals)            43.2 MB   53 s
#   returnZ=false&returnM=false            43.2 MB   46 s   <- silently ignored
#   + geometryPrecision=6                  28.8 MB   29 s
#   + maxAllowableOffset=0.001 (~100 m)     2.4 MB   10 s   <- 18x smaller
#
# maxAllowableOffset is server-side Douglas-Peucker in output-CRS units, so 0.001
# degrees is roughly 100 m at the equator. That is not a shortcut: at 1:250,000 a
# half-millimetre of map is 125 m on the ground, so a 100 m tolerance discards
# precision the source never had, and it is 1% of a 10 km analysis cell. Both
# values are recorded in the output file so a reader knows what they have.
DEFAULT_MAX_OFFSET = 0.001
DEFAULT_PRECISION = 6
USER_AGENT = "indonesia-sez-research/0.1 (academic use; contact via repo)"


def _ring_is_clockwise(ring: list) -> bool:
    """Shoelace test. In Esri polygons an EXTERIOR ring is clockwise and a hole
    is counter-clockwise, which is how one flat `rings` list encodes holes and
    multi-part polygons at the same time."""
    area = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        area += x1 * y2 - x2 * y1
    return area < 0          # y-up shoelace: CCW positive, so CW is negative


def esri_to_geojson(feat: dict, geom_type: str) -> dict:
    """Convert one Esri-JSON feature to a GeoJSON feature.

    Needed because BIG's own GeoJSON writer refuses some geometries its Esri-JSON
    writer emits happily — a degenerate zero-area polygon, for instance. Rather
    than lose those features, the fetcher retries the page as Esri JSON and
    converts here.
    """
    g = feat.get("geometry") or {}
    out: dict | None = None

    if geom_type == "esriGeometryPolygon" and "rings" in g:
        polys: list[list] = []
        for ring in g["rings"]:
            # GeoJSON (RFC 7946) wants exterior CCW and holes CW — the opposite
            # of Esri — so each ring is reversed as it is copied.
            flat = [[pt[0], pt[1]] for pt in ring]
            if _ring_is_clockwise(ring):
                polys.append([flat[::-1]])        # new exterior ring
            elif polys:
                polys[-1].append(flat[::-1])      # a hole in the previous one
            else:
                polys.append([flat[::-1]])        # hole with no exterior: keep it
        if len(polys) == 1:
            out = {"type": "Polygon", "coordinates": polys[0]}
        elif polys:
            out = {"type": "MultiPolygon", "coordinates": polys}

    elif geom_type == "esriGeometryPolyline" and "paths" in g:
        paths = [[[pt[0], pt[1]] for pt in path] for path in g["paths"]]
        if len(paths) == 1:
            out = {"type": "LineString", "coordinates": paths[0]}
        elif paths:
            out = {"type": "MultiLineString", "coordinates": paths}

    elif geom_type == "esriGeometryPoint" and "x" in g:
        out = {"type": "Point", "coordinates": [g["x"], g["y"]]}

    elif geom_type == "esriGeometryMultipoint" and "points" in g:
        out = {"type": "MultiPoint",
               "coordinates": [[p[0], p[1]] for p in g["points"]]}

    attrs = feat.get("attributes") or {}
    return {"type": "Feature", "geometry": out, "properties": attrs,
            "id": attrs.get("OBJECTID") or attrs.get("FID")}


def degenerate_ring_count(features: list[dict]) -> int:
    """How many polygon rings have fewer than 3 distinct positions.

    Such a ring is not a valid GeoJSON polygon. They are kept rather than
    dropped, so the feature count still matches the server's, but they are
    counted and reported — a silently discarded feature is the thing this
    script exists to prevent."""
    n = 0
    for f in features:
        g = f.get("geometry") or {}
        if g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        polys = ([g["coordinates"]] if g["type"] == "Polygon"
                 else g["coordinates"])
        for poly in polys:
            for ring in poly:
                if len({(p[0], p[1]) for p in ring}) < 3:
                    n += 1
    return n


def geometry_params(out_sr: int, max_offset: float | None,
                    precision: int | None) -> dict:
    """The parameters that control how much geometry comes back."""
    p: dict[str, str] = {"returnGeometry": "true", "outSR": str(out_sr),
                         # Asked for even though BIG ignores them on some layers:
                         # harmless where ignored, a real saving where honoured.
                         "returnZ": "false", "returnM": "false"}
    if precision is not None:
        p["geometryPrecision"] = str(precision)
    if max_offset:
        p["maxAllowableOffset"] = repr(max_offset)
    return p


def get(url: str, params: dict, timeout: int = 300, retries: int = 5) -> dict:
    """One GET returning parsed JSON, with retries and exponential backoff.

    Public GIS servers time out and rate-limit; a transient failure is normal
    and is not a reason to lose an hour of paging. But note what is NOT retried:
    a response that parses as JSON and contains an ArcGIS `error` object is
    returned as-is, because retrying a malformed query just asks the same wrong
    question five times.
    """
    query = urllib.parse.urlencode(params)
    full = f"{url}?{query}"
    last_err: Exception | None = None

    for attempt in range(retries):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_err = exc
            if attempt < retries - 1:
                wait = 2 ** attempt          # 1, 2, 4, 8 seconds
                print(f"      retry {attempt + 1}/{retries - 1} in {wait}s ({exc})",
                      file=sys.stderr)
                time.sleep(wait)

    raise RuntimeError(f"giving up on {url} after {retries} attempts: {last_err}")


def layer_info(service: str, layer: int) -> dict:
    """Metadata for one layer: name, geometry type, page size, field list."""
    info = get(f"{BASE}/{service}/MapServer/{layer}", {"f": "json"})
    if "error" in info:
        raise RuntimeError(f"layer metadata failed: {info['error']}")
    return info


def supports_pagination(info: dict) -> bool:
    """Whether the layer accepts resultOffset/resultRecordCount at all.

    Not every BIG service does. PPIG/IDX_Download rejects the parameters
    outright with 'Pagination is not supported', so a fetcher that always sends
    them cannot read those layers. Checked here rather than discovered by a
    400 halfway through.
    """
    adv = info.get("advancedQueryCapabilities") or {}
    return bool(adv.get("supportsPagination"))


def oid_field(info: dict) -> str:
    """Name of the object-id field, which is not always 'OBJECTID' (can be 'FID')."""
    if info.get("objectIdField"):
        return info["objectIdField"]
    for f in info.get("fields", []):
        if f.get("type") == "esriFieldTypeOID":
            return f["name"]
    return "OBJECTID"


def feature_count(service: str, layer: int, where: str) -> int:
    """How many features the query SHOULD return. This is the denominator."""
    res = get(
        f"{BASE}/{service}/MapServer/{layer}/query",
        {"where": where, "returnCountOnly": "true", "f": "json"},
    )
    if "error" in res:
        raise RuntimeError(f"count failed: {res['error']}")
    return int(res["count"])


def _fetch_by_oid_range(url: str, where: str, fields: str, geom: dict,
                        step: int, oid: str, expected: int) -> list[dict]:
    """Walk the layer in object-id windows, for layers that reject paging.

    `where` is ANDed with `oid >= lo AND oid < hi`, so each request is an
    ordinary filtered query rather than an offset. Object ids are not
    guaranteed contiguous, so a window can come back with fewer rows than
    `step` without anything being wrong — which is exactly why the total is
    still checked against the server's own count at the end.
    """
    stats = get(url, {
        "where": where, "f": "json",
        "outStatistics": json.dumps([
            {"statisticType": "min", "onStatisticField": oid, "outStatisticFieldName": "lo"},
            {"statisticType": "max", "onStatisticField": oid, "outStatisticFieldName": "hi"},
        ]),
    })
    if "error" in stats:
        raise RuntimeError(f"could not read {oid} range: {stats['error']}")
    attrs = stats["features"][0]["attributes"]
    lo, hi = int(attrs["lo"]), int(attrs["hi"])
    print(f"    {oid} spans {lo:,}–{hi:,}", flush=True)

    features: list[dict] = []
    start, window = lo, 0
    while start <= hi:
        window += 1
        end = start + step
        clause = f"({where}) AND {oid} >= {start} AND {oid} < {end}"
        res = get(url, {"where": clause, "outFields": fields,
                        "f": "geojson", **geom})
        if "error" in res:
            raise RuntimeError(f"{oid} window {start}-{end} failed: {res['error']}")
        batch = res.get("features", [])
        features.extend(batch)
        pct = 100 * len(features) / expected
        print(f"    window {window:>4} [{start:>8},{end:>8})  +{len(batch):>5}  "
              f"total {len(features):>7,} / {expected:,}  ({pct:5.1f}%)", flush=True)
        start = end

    if len(features) != expected:
        raise RuntimeError(
            f"MISMATCH: {oid} scan collected {len(features):,}, "
            f"server said {expected:,}. Refusing to write a partial file.")
    return features


def fetch_all(service: str, layer: int, where: str, geom: dict,
              page_size: int, fields: str, info: dict) -> list[dict]:
    """Page through the layer and return a list of GeoJSON features."""
    expected = feature_count(service, layer, where)
    print(f"  server reports {expected:,} features matching where={where!r}", flush=True)
    if expected == 0:
        return []

    url = f"{BASE}/{service}/MapServer/{layer}/query"
    oid = oid_field(info)

    if not supports_pagination(info):
        # No offset paging available. Two cases, and only one is safe to guess at.
        if expected <= page_size:
            print(f"  layer does not support pagination; {expected:,} features fit "
                  f"in one request (limit {page_size})", flush=True)
            res = get(url, {"where": where, "outFields": fields,
                            "f": "geojson", **geom})
            if "error" in res:
                raise RuntimeError(f"single-shot query failed: {res['error']}")
            feats = res.get("features", [])
            if len(feats) != expected:
                raise RuntimeError(
                    f"MISMATCH: single request returned {len(feats):,}, "
                    f"server said {expected:,}.")
            return feats
        # Larger than one request and no paging: walk ranges of the object id
        # instead. Slower and needs the ids to be reasonably dense, but correct.
        print(f"  layer does not support pagination and {expected:,} > {page_size}; "
              f"falling back to {oid} range scanning", flush=True)
        return _fetch_by_oid_range(url, where, fields, geom, page_size,
                                   oid, expected)
    features: list[dict] = []
    seen: set[object] = set()       # OBJECTIDs, to catch duplicate pages
    offset = 0
    page = 0

    while offset < expected:
        page += 1
        params_base = {
            "where": where,
            "outFields": fields,
            # Stable ordering is what makes resultOffset mean anything at all.
            "orderByFields": f"{oid} ASC",
            "resultOffset": str(offset),
            "resultRecordCount": str(page_size),
            **geom,
        }
        res = get(url, {**params_base, "f": "geojson"})

        if "error" in res:
            # BIG's GeoJSON writer chokes on some geometries its Esri-JSON writer
            # handles. Retry the same page as Esri JSON and convert client-side
            # before treating this as a real failure.
            print(f"      page {page} failed as geojson ({res['error'].get('message')}); "
                  f"retrying as Esri JSON", flush=True)
            alt = dict(params_base)
            alt["f"] = "json"
            res2 = get(url, alt)
            if "error" in res2:
                raise RuntimeError(
                    f"page {page} (offset {offset}) failed in both formats: "
                    f"geojson={res['error']} esrijson={res2['error']}")
            gtype = res2.get("geometryType") or info.get("geometryType")
            res = {"features": [esri_to_geojson(f, gtype)
                                for f in res2.get("features", [])]}
            print(f"      recovered {len(res['features'])} features via Esri JSON",
                  flush=True)

        batch = res.get("features", [])
        if not batch:
            # Ran dry before reaching the expected count: report, don't paper over.
            raise RuntimeError(
                f"page {page} returned 0 features at offset {offset}, "
                f"but {expected:,} were expected ({len(features):,} collected). "
                "The server truncated the result set."
            )

        for feat in batch:
            oid = (feat.get("id")
                   or (feat.get("properties") or {}).get("OBJECTID"))
            if oid is not None:
                if oid in seen:
                    raise RuntimeError(
                        f"OBJECTID {oid} arrived twice — paging is returning "
                        "overlapping pages, so the download cannot be trusted."
                    )
                seen.add(oid)
            features.append(feat)

        offset += len(batch)
        pct = 100 * len(features) / expected
        # flush=True: stdout is block-buffered when redirected to a file, so
        # without this a long background run shows no progress at all until it ends.
        print(f"    page {page:>4}  +{len(batch):>5}  "
              f"total {len(features):>7,} / {expected:,}  ({pct:5.1f}%)", flush=True)

    # The gate. Everything above can succeed while this still fails.
    if len(features) != expected:
        raise RuntimeError(
            f"MISMATCH: collected {len(features):,} features, "
            f"server said {expected:,}. Refusing to write a partial file."
        )

    return features


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--service", required=True,
                    help="folder/service, e.g. PTRA/Atlas_Transportasi_Darat")
    ap.add_argument("--layer", required=True, type=int, help="numeric layer id")
    ap.add_argument("--out", required=True, help="output .geojson path")
    ap.add_argument("--where", default="1=1",
                    help="SQL filter; default 1=1 (every feature)")
    ap.add_argument("--fields", default="*", help="outFields; default *")
    ap.add_argument("--out-sr", type=int, default=4326,
                    help="output EPSG; default 4326 (WGS84 lon/lat)")
    ap.add_argument("--max-offset", type=float, default=DEFAULT_MAX_OFFSET,
                    help="server-side simplification tolerance in output-CRS units "
                         f"(default {DEFAULT_MAX_OFFSET}, ~100 m in degrees). "
                         "Pass 0 for undecimated geometry — expect ~18x the size.")
    ap.add_argument("--geometry-precision", type=int, default=DEFAULT_PRECISION,
                    help=f"decimal places in coordinates (default {DEFAULT_PRECISION}, ~0.1 m)")
    ap.add_argument("--page-size", type=int, default=None,
                    help="records per request; default = the layer's maxRecordCount")
    args = ap.parse_args()

    print(f"BIG layer fetch — {args.service}/{args.layer}")
    info = layer_info(args.service, args.layer)
    page_size = args.page_size or int(info.get("maxRecordCount") or 1000)
    print(f"  layer name    : {info.get('name')!r}")
    print(f"  geometry      : {info.get('geometryType')}")
    print(f"  page size     : {page_size}"
          + ("" if args.page_size else " (the layer's own maxRecordCount)"))
    print(f"  output CRS    : EPSG:{args.out_sr}")

    print(f"  pagination    : {'yes' if supports_pagination(info) else 'NO — using fallback'}")
    geom = geometry_params(args.out_sr, args.max_offset, args.geometry_precision)
    print(f"  simplification: maxAllowableOffset={args.max_offset or 'none'} "
          f"geometryPrecision={args.geometry_precision}")
    features = fetch_all(args.service, args.layer, args.where,
                         geom, page_size, args.fields, info)

    # The CRS is written explicitly. GeoJSON is *defined* as WGS84, so a reader
    # will assume 4326 whatever the coordinates actually are — which means a file
    # fetched in any other CRS is silently mislabelled unless it says so.
    fc = {
        "type": "FeatureCollection",
        "name": info.get("name"),
        "crs": {"type": "name",
                "properties": {"name": f"urn:ogc:def:crs:EPSG::{args.out_sr}"}},
        "features": features,
        "fetched_from": f"{BASE}/{args.service}/MapServer/{args.layer}",
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "fetched_where": args.where,
        # Recorded so nobody has to guess later how decimated this geometry is.
        "fetch_max_allowable_offset": args.max_offset,
        "fetch_geometry_precision": args.geometry_precision,
        "degenerate_rings": degenerate_ring_count(features),
    }

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(fc, fh)

    bad = degenerate_ring_count(features)
    if bad:
        print(f"  NOTE: {bad} polygon ring(s) have fewer than 3 distinct points — "
              "zero-area slivers in the source. Kept (so the count still matches), "
              "but they are not valid GeoJSON polygons; clean them before use, "
              "e.g. shapely make_valid / .buffer(0).")

    import os
    size_mb = os.path.getsize(args.out) / 1e6
    print(f"  WROTE {args.out}  ({len(features):,} features, {size_mb:.1f} MB)")
    print("  count verified against the server's own total.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, KeyboardInterrupt) as exc:
        print(f"\nFAILED: {exc}", file=sys.stderr)
        sys.exit(1)
