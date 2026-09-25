from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import requests

from .download import checked_json, save_json
from .metadata import status_update, relative

LOG = logging.getLogger(__name__)


def fetch_layer(client: requests.Session, url: str, source_id: str, folder: Path, where: str, *, batch_size: int = 1000, timeout: int = 60) -> dict[str, Any]:
    """Freeze an ID list, fetch each ID once, and reconcile with the service."""
    folder.mkdir(parents=True, exist_ok=True)
    metadata, headers = checked_json(client, url, params={"f": "json"}, timeout=timeout)
    save_json(folder / "layer_metadata.json", metadata, source_id, command=f"GET {url}?f=json", headers=headers)
    oid = metadata.get("objectIdField") or metadata.get("objectIdFieldName")
    if not oid:
        oid_fields = [field["name"] for field in metadata.get("fields", []) if field.get("type") == "esriFieldTypeOID"]
        oid = oid_fields[0] if len(oid_fields) == 1 else None
    if not oid or not metadata.get("fields"):
        raise ValueError(f"No object ID or fields in layer metadata: {url}")
    limit = min(int(metadata.get("maxRecordCount", batch_size)), batch_size)
    query = url.rstrip("/") + "/query"
    base = {"f": "json", "where": where}
    count, _ = checked_json(client, query, params={**base, "returnCountOnly": "true"}, timeout=timeout)
    ids_response, _ = checked_json(client, query, params={**base, "returnIdsOnly": "true"}, timeout=timeout)
    ids = ids_response.get("objectIds") or []
    if count.get("count") != len(ids) or len(ids) != len(set(ids)):
        raise ValueError(f"ArcGIS count/ID mismatch: count={count.get('count')} IDs={len(ids)}")
    save_json(folder / "ids.json", {"where": where, "objectIdField": oid, "count": len(ids), "objectIds": sorted(ids), "dataLastEditDate": metadata.get("editingInfo", {}).get("dataLastEditDate")}, source_id, command=f"GET {query} returnIdsOnly")
    ordered = sorted(ids)
    requests_log = {"layer_url": url, "where": where, "batch_size": limit, "outSR": 4326, "query_method": "POST", "object_id_field": oid}
    save_json(folder / "query_parameters.json", requests_log, source_id, command="record ArcGIS query parameters")
    fetched: set[int] = set()
    for offset in range(0, len(ordered), limit):
        batch_ids = ordered[offset:offset + limit]
        target = folder / f"batch_{offset:07d}.json"
        if target.exists():
            value = json.loads(target.read_text())
            if "error" in value:
                raise ValueError(f"Stored ArcGIS error: {target}")
        else:
            params = {"f": "json", "objectIds": ",".join(str(item) for item in batch_ids), "outFields": "*", "returnGeometry": "true", "outSR": "4326"}
            value, batch_headers = checked_json(client, query, params=params, timeout=timeout, method="POST")
            if value.get("exceededTransferLimit"):
                raise ValueError(f"ArcGIS batch exceeded transfer limit: {target}")
            save_json(target, value, source_id, command=f"POST {query} objectIds={batch_ids[0]}..{batch_ids[-1]}", headers=batch_headers)
        features = value.get("features")
        if not isinstance(features, list):
            raise ValueError(f"Missing features: {target}")
        got = {feature["attributes"][oid] for feature in features}
        if got != set(batch_ids) or got & fetched:
            raise ValueError(f"ArcGIS missing/extra/duplicate IDs: {target}")
        fetched.update(got)
        if offset % 25000 == 0:
            LOG.info("%s: %s/%s records", source_id, len(fetched), len(ordered))
    final_count, _ = checked_json(client, query, params={**base, "returnCountOnly": "true"}, timeout=timeout)
    final_meta, _ = checked_json(client, url, params={"f": "json"}, timeout=timeout)
    stable = final_count.get("count") == len(fetched) and final_meta.get("editingInfo", {}).get("dataLastEditDate") == metadata.get("editingInfo", {}).get("dataLastEditDate")
    result = {"count": len(fetched), "server_count_final": final_count.get("count"), "stable_snapshot": stable, "data_last_edit_date": metadata.get("editingInfo", {}).get("dataLastEditDate"), "folder": relative(folder)}
    save_json(folder / "reconciliation.json", result, source_id, command="reconcile ArcGIS IDs, count and source version")
    status_update(source_id, "verified" if stable else "partial", "ArcGIS ID and count reconciliation" if stable else "Source changed during extraction; review snapshot", **result)
    return result
