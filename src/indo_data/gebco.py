from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import rasterio
from netCDF4 import Dataset
from rasterio.transform import from_origin

from .download import session
from .metadata import ROOT, atomic_json, register, status_update, verify_manifest_entry

LOG = logging.getLogger(__name__)


def _bounds_indices(values: np.ndarray, lower: float, upper: float) -> tuple[int, int]:
    start = int(np.searchsorted(values, lower, side="left"))
    end = int(np.searchsorted(values, upper, side="right"))
    if not (0 <= start < end <= len(values)):
        raise ValueError("Invalid GEBCO subset bounds")
    return start, end


def fetch_gebco(urls: dict[str, str], bbox: list[float], folder: Path, *, block_rows: int, max_single_bytes: int) -> dict:
    """Materialize native-resolution CEDA OPeNDAP arrays as versioned NetCDF subsets."""
    folder.mkdir(parents=True, exist_ok=True)
    client = session(2)
    result = {}
    for kind, variable in (("elevation", "elevation"), ("tid", "tid")):
        url = urls[kind + "_opendap_url"]
        for suffix in ("dds", "das"):
            meta_path = folder / f"{kind}.{suffix}"
            if meta_path.exists():
                verify_manifest_entry(meta_path)
            else:
                response = client.get(url + "." + suffix, timeout=45)
                response.raise_for_status()
                if "Dataset" not in response.text and "Attributes" not in response.text:
                    raise ValueError(f"Unexpected OPeNDAP {suffix} response")
                meta_path.write_text(response.text)
                register(meta_path, "gebco_2026", suffix.upper(), command=f"GET {url}.{suffix}", headers=dict(response.headers))
        target = folder / f"gebco_2026_{kind}_regional.nc"
        if target.exists():
            verify_manifest_entry(target)
            with Dataset(target) as existing:
                if variable not in existing.variables or len(existing.dimensions["lat"]) < 100 or len(existing.dimensions["lon"]) < 100:
                    raise ValueError(f"Invalid existing GEBCO subset: {target}")
                result[kind] = {"path": str(target), "shape": (len(existing.dimensions["lat"]), len(existing.dimensions["lon"]))}
            continue
        temp = target.with_name(target.name + ".part")
        temp.unlink(missing_ok=True)
        with Dataset(url) as remote:
            lat = np.asarray(remote.variables["lat"][:])
            lon = np.asarray(remote.variables["lon"][:])
            x0, x1 = _bounds_indices(lon, bbox[0], bbox[2])
            y0, y1 = _bounds_indices(lat, bbox[1], bbox[3])
            selected_lat = lat[y0:y1]
            selected_lon = lon[x0:x1]
            expected_width = round((bbox[2] - bbox[0]) * 240)
            expected_height = round((bbox[3] - bbox[1]) * 240)
            if len(selected_lon) != expected_width or len(selected_lat) != expected_height:
                raise ValueError(f"Unexpected GEBCO native-grid subset shape: {len(selected_lat)}x{len(selected_lon)}")
            if len(selected_lon) * len(selected_lat) * (2 if kind == "elevation" else 1) > max_single_bytes:
                raise ValueError("GEBCO subset exceeds configured single-download limit")
            with Dataset(temp, "w", format="NETCDF4") as local:
                local.createDimension("lat", len(selected_lat))
                local.createDimension("lon", len(selected_lon))
                yvar = local.createVariable("lat", "f8", ("lat",))
                xvar = local.createVariable("lon", "f8", ("lon",))
                yvar[:] = selected_lat
                xvar[:] = selected_lon
                for name, output in (("lat", yvar), ("lon", xvar)):
                    for attr in remote.variables[name].ncattrs():
                        output.setncattr(attr, remote.variables[name].getncattr(attr))
                source = remote.variables[variable]
                dtype = "i2" if kind == "elevation" else "u1"
                data = local.createVariable(variable, dtype, ("lat", "lon"), zlib=True, complevel=2, chunksizes=(min(block_rows, len(selected_lat)), min(1200, len(selected_lon))))
                for attr in source.ncattrs():
                    if attr not in ("_FillValue",):
                        data.setncattr(attr, source.getncattr(attr))
                for attr in remote.ncattrs():
                    if attr not in ("geospatial_bounds",):
                        local.setncattr(attr, remote.getncattr(attr))
                local.setncattr("subset_bbox_requested", json.dumps(bbox))
                local.setncattr("opendap_source_url", url)
                local.setncattr("opendap_constraint", f"{variable}[{y0}:{y1-1}][{x0}:{x1-1}]")
                local.setncattr("subset_note", "Native 15 arc-second values and coordinates, no resampling")
                for begin in range(y0, y1, block_rows):
                    end = min(begin + block_rows, y1)
                    block = source[begin:end, x0:x1]
                    if np.ma.is_masked(block) and np.ma.getmaskarray(block).any():
                        raise ValueError("Unexpected masked GEBCO values")
                    data[begin - y0:end - y0, :] = np.asarray(block)
                    if (begin - y0) % 1024 == 0:
                        LOG.info("GEBCO %s: %s/%s rows", kind, end - y0, y1 - y0)
        temp.replace(target)
        with Dataset(target) as reopened:
            if reopened.variables[variable].shape != (y1 - y0, x1 - x0):
                raise ValueError("GEBCO subset failed reopen shape check")
        register(target, "gebco_2026", "NetCDF4", extent=str((float(selected_lon[0]), float(selected_lat[0]), float(selected_lon[-1]), float(selected_lat[-1]))), rows=f"{y1-y0}x{x1-x0}", command=f"OPeNDAP {variable}[{y0}:{y1-1}][{x0}:{x1-1}]")
        result[kind] = {"path": str(target), "shape": (y1 - y0, x1 - x0)}
    atomic_json(folder / "subset_request.json", {"bbox": bbox, "urls": urls, "result": result, "native_spacing_arcseconds": 15})
    register(folder / "subset_request.json", "gebco_2026", "JSON")
    status_update("gebco_2026", "downloaded", "Elevation and matching TID native-grid OPeNDAP subsets materialized and reopened", **result)
    return result


def process_gebco(folder: Path, snapshot: str) -> dict:
    output = ROOT / "data/processed/coast_bathymetry" / snapshot
    output.mkdir(parents=True, exist_ok=True)
    result = {}
    for kind, variable in (("elevation", "elevation"), ("tid", "tid")):
        source_path = folder / f"gebco_2026_{kind}_regional.nc"
        with Dataset(source_path) as source:
            lat = np.asarray(source.variables["lat"][:])
            lon = np.asarray(source.variables["lon"][:])
            spacing = float(lon[1] - lon[0])
            if not np.allclose(np.diff(lat), spacing, atol=1e-7) or not np.allclose(np.diff(lon), spacing, atol=1e-7):
                raise ValueError("GEBCO coordinate spacing not regular")
            height, width = source.variables[variable].shape
            transform = from_origin(float(lon[0] - spacing / 2), float(lat[-1] + spacing / 2), spacing, spacing)
            target = output / f"gebco_2026_{kind}_regional.tif"
            dtype = "int16" if kind == "elevation" else "uint8"
            with rasterio.open(target, "w", driver="GTiff", width=width, height=height, count=1, dtype=dtype, crs="EPSG:4326", transform=transform, tiled=True, compress="deflate", predictor=2 if kind == "elevation" else 1, blockxsize=256, blockysize=256) as dest:
                for begin in range(0, height, 128):
                    end = min(begin + 128, height)
                    values = np.asarray(source.variables[variable][begin:end, :])
                    dest.write(np.flipud(values), 1, window=((height - end, height - begin), (0, width)))
                dest.update_tags(source="GEBCO_2026", variable=variable, note="Native values; rows reversed north-up, no resampling")
        with rasterio.open(target) as reopened:
            if reopened.shape != (height, width) or reopened.crs.to_epsg() != 4326:
                raise ValueError("GEBCO GeoTIFF failed reopen check")
            bounds = tuple(reopened.bounds)
        register(target, "gebco_2026", "GeoTIFF", extent=str(bounds), rows=f"{height}x{width}", parents=str(source_path.relative_to(ROOT)), command="python -m indo_data process --all")
        result[kind] = {"shape": (height, width), "bounds": bounds, "path": str(target.relative_to(ROOT))}
    status_update("gebco_2026", "verified", "Native-resolution elevation and TID GeoTIFFs reopened; signed elevation and TID categories retained", **result)
    return result
