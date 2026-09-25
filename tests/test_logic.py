from datetime import date

import pandas as pd
import pytest
import geopandas as gpd
from shapely.geometry import box

from indo_data.port_activity import aggregate_activity
from indo_data.policy_treatment import possible_treatment_status
from indo_data.ports_historical import evidence_presence
from indo_data.osm_policy import _admin_matches, _site_name_eligible, polygon_eligible


def test_aggregation_keeps_missing_distinct_from_zero_and_leap_year():
    daily = pd.DataFrame({"port_id": ["p", "p"], "date": ["2020-02-01", "2020-02-29"], "portcalls_container": [None, None], "portcalls_tanker": [0, 2]})
    monthly = aggregate_activity(daily, "month", ["portcalls_container", "portcalls_tanker"])
    row = monthly.iloc[0]
    assert row.expected_calendar_days == 29
    assert row.observed_days == 2
    assert row.partial_period
    assert pd.isna(row.portcalls_container)
    assert row.portcalls_container_missing_days == 29
    assert row.portcalls_tanker == 2
    assert row.portcalls_tanker_missing_days == 27


def test_policy_status_is_unknown_in_event_year_and_without_complete_registry():
    designation = date(1998, 7, 1)
    assert possible_treatment_status(1998, designation, None) == "unknown"
    assert possible_treatment_status(1999, designation, None) == "treated"
    assert possible_treatment_status(1997, designation, None) == "unknown"
    assert possible_treatment_status(1997, designation, None, complete_registry=True) == "not_treated"
    assert possible_treatment_status(2000, designation, date(2000, 4, 2)) == "unknown"


def test_historical_listing_does_not_imply_continuity_or_absence():
    assert evidence_presence(1992, {1992, 1995}) == "documented_present"
    assert evidence_presence(1993, {1992, 1995}) == "unknown"
    assert evidence_presence(2000, {1992, 1995}) == "unknown"


def test_partial_wording_never_qualifies_for_whole_admin_polygon():
    base = {"name": "Kapuas", "region": "kalimantan", "level": 5}
    assert not polygon_eligible({**base, "scope": "partial_admin"})
    assert not polygon_eligible({**base, "scope": "whole_island"})
    assert polygon_eligible({**base, "scope": "whole_admin"})


def test_ambiguous_names_require_review_even_with_matching_province():
    admin = gpd.GeoDataFrame([
        {"name": "Kalimantan Tengah", "fclass": "admin_level4", "geometry": box(0, 0, 10, 10)},
        {"name": "Kapuas", "fclass": "admin_level5", "geometry": box(1, 1, 2, 2)},
        {"name": "Kabupaten Kapuas", "fclass": "admin_level5", "geometry": box(3, 3, 4, 4)},
    ], crs="EPSG:4326")
    matches = _admin_matches(admin, {"name": "Kapuas", "level": 5, "province": "Kalimantan Tengah"})
    assert len(matches) == 2


def test_kek_city_name_cannot_be_site_polygon():
    assert not _site_name_eligible("Palu", "Palu")
    assert not _site_name_eligible("Nongsa", "Nongsa")
    assert _site_name_eligible("Kawasan Ekonomi Khusus Palu", "Palu")
