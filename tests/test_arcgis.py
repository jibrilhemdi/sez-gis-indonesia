import json

import pytest

from indo_data.arcgis import fetch_layer


class FakeResponse:
    def __init__(self, value):
        self.value = value
        self.headers = {"Content-Type": "application/json"}
        self.content = json.dumps(value).encode()

    def raise_for_status(self):
        pass

    def json(self):
        return self.value


class FakeClient:
    def __init__(self, *, change=False):
        self.change = change
        self.metadata_calls = 0

    def request(self, method, url, params=None, data=None, timeout=None):
        p = params if method == "GET" else data
        if url.endswith("/query"):
            if p.get("returnCountOnly") == "true":
                return FakeResponse({"count": 3})
            if p.get("returnIdsOnly") == "true":
                return FakeResponse({"objectIds": [1, 2, 3]})
            ids = [int(x) for x in p["objectIds"].split(",")]
            return FakeResponse({"features": [{"attributes": {"ObjectId": oid}} for oid in ids]})
        self.metadata_calls += 1
        edit = 2 if self.change and self.metadata_calls > 1 else 1
        return FakeResponse({"objectIdField": "ObjectId", "fields": [{"name": "ObjectId"}], "maxRecordCount": 2, "editingInfo": {"dataLastEditDate": edit}})


def test_arcgis_batches_and_reconciles(tmp_path, monkeypatch):
    from indo_data import arcgis
    monkeypatch.setattr(arcgis, "save_json", lambda path, value, *args, **kwargs: path.write_text(json.dumps(value)))
    monkeypatch.setattr(arcgis, "status_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(arcgis, "relative", lambda path: path.name)
    result = fetch_layer(FakeClient(), "https://example.test/layer", "test", tmp_path, "1=1", batch_size=2)
    assert result["count"] == 3
    assert result["stable_snapshot"]
    assert len(list(tmp_path.glob("batch_*.json"))) == 2


def test_arcgis_detects_revision(tmp_path, monkeypatch):
    from indo_data import arcgis
    monkeypatch.setattr(arcgis, "save_json", lambda path, value, *args, **kwargs: path.write_text(json.dumps(value)))
    monkeypatch.setattr(arcgis, "status_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(arcgis, "relative", lambda path: path.name)
    result = fetch_layer(FakeClient(change=True), "https://example.test/layer", "test", tmp_path, "1=1", batch_size=2)
    assert not result["stable_snapshot"]
