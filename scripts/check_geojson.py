#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Sanity-check a fetched GeoJSON: extent, geometry types, empty geometries.

A verified feature COUNT says nothing about whether the geometry is in the right
place. The cheapest real check is the bounding box: Indonesia spans roughly
95E-141E and 11S-6N, so anything outside that means the CRS was mislabelled or
the server handed back a different projection than was asked for — the failure
mode that produces a map of the Gulf of Guinea (0,0) or of nowhere at all.
"""
import json, sys, collections

# Indonesia's approximate extent, generous at the edges.
IDN = (94.0, -12.0, 142.5, 6.2)
# A much looser box. Outside THIS, the coordinates cannot be Indonesian at all and
# the likely cause is a CRS problem; between the two boxes the likely cause is
# simply that the layer includes neighbouring countries, which BIG's atlases do —
# Borneo is shared with Malaysia and Brunei, and the Malacca coastline runs into
# Malaysia and Thailand. Two different diagnoses, so two different messages.
PLAUSIBLE = (88.0, -16.0, 148.0, 12.0)

def walk(coords):
    """Yield (x, y) from any nesting depth of GeoJSON coordinates."""
    if not coords:
        return
    if isinstance(coords[0], (int, float)):
        yield coords[0], coords[1]
        return
    for c in coords:
        yield from walk(c)

for path in sys.argv[1:]:
    with open(path) as fh:
        fc = json.load(fh)
    feats = fc.get("features", [])
    types = collections.Counter(
        (f.get("geometry") or {}).get("type") for f in feats)
    empty = sum(1 for f in feats if not (f.get("geometry") or {}).get("coordinates"))

    xs, ys, nvert = [], [], 0
    for f in feats:
        g = f.get("geometry") or {}
        for x, y in walk(g.get("coordinates") or []):
            xs.append(x); ys.append(y); nvert += 1

    print(f"\n{path}")
    print(f"  features     {len(feats):,}   vertices {nvert:,}"
          f"   mean {nvert / max(len(feats), 1):.1f} per feature")
    print(f"  geometry     {dict(types)}")
    print(f"  empty geom   {empty}")
    print(f"  offset/prec  {fc.get('fetch_max_allowable_offset')} / "
          f"{fc.get('fetch_geometry_precision')}")
    if xs:
        bbox = (min(xs), min(ys), max(xs), max(ys))
        print(f"  bbox         {bbox[0]:.3f}, {bbox[1]:.3f}, {bbox[2]:.3f}, {bbox[3]:.3f}")
        def within(box):
            return (box[0] <= bbox[0] and box[1] <= bbox[1]
                    and bbox[2] <= box[2] and bbox[3] <= box[3])
        if within(IDN):
            print("  extent       within Indonesia")
        elif within(PLAUSIBLE):
            print("  extent       extends BEYOND Indonesia but plausibly regional — "
                  "expect neighbouring-country features (Malaysia, Brunei, "
                  "Timor-Leste, PNG). Filter on a country attribute if the layer "
                  "has one (NEGARA, NAMOBJ).")
        else:
            print("  extent       IMPLAUSIBLE — almost certainly a CRS problem; "
                  "the file claims WGS84 but the coordinates are not lon/lat.")
    if empty:
        print("  WARNING: empty geometries present — simplification can collapse a "
              "feature smaller than the tolerance to nothing.")
