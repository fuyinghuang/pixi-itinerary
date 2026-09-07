"""Behaviour we add on top of the supplied catalogue.

Supplied-data validation (image counts, room categories, rate types, tag
vocabulary) belongs to `data/validate.py` and is deliberately not repeated
here.
"""

from __future__ import annotations

from typing import Any, Dict, Set

import pytest

from app import catalogue
from app.catalogue import TripRegion, UnknownCountryError

EXPECTED_MEMBERSHIP: Dict[TripRegion, Set[str]] = {
    TripRegion.SOUTH_AFRICA: {
        "ellerman-house-cape-town",
        "delaire-graff-stellenbosch",
        "londolozi-sabi-sand",
    },
    TripRegion.EAST_AFRICA: {
        "giraffe-manor-nairobi",
        "angama-mara",
        "andbeyond-ngorongoro",
        "singita-grumeti",
    },
    TripRegion.JAPAN: {
        "aman-tokyo",
        "park-hyatt-kyoto",
        "hoshinoya-kyoto",
    },
    TripRegion.ITALY: {
        "hotel-de-russie-rome",
        "belmond-caruso-ravello",
    },
}


def _record(country: str) -> Dict[str, Any]:
    """A minimal well-formed record, for cases the supplied data cannot cover."""
    return {
        "id": "test-hotel",
        "name": "Test Hotel",
        "brand": None,
        "country": country,
        "region": "Test Region",
        "city": "Test City",
        "latitude": 0.0,
        "longitude": 0.0,
        "nearest_airport": {"iata": "TST", "name": "Test Airport"},
        "description": "A property that exists only in this test.",
        "tags": ["luxury"],
        "approx_nightly_rate": 100,
        "currency": "USD",
        "images": ["a", "b", "c"],
        "rooms": [{"name": "Base", "rate_delta": 0}],
    }


def test_all_supplied_hotels_load():
    assert len(catalogue.all_hotels()) == 12


def test_known_ids_resolve():
    for hotel in catalogue.all_hotels():
        assert catalogue.get(hotel.id) is hotel


def test_unknown_id_returns_none():
    assert catalogue.get("no-such-hotel") is None


def test_every_supplied_country_maps_to_exactly_one_region():
    supplied = {hotel.country for hotel in catalogue.all_hotels()}

    # No supplied country is unmapped, and the map carries no dead entries.
    assert set(catalogue.COUNTRY_TO_TRIP_REGION) == supplied

    for hotel in catalogue.all_hotels():
        assert isinstance(catalogue.trip_region_of(hotel), TripRegion)


def test_region_membership_is_exact():
    for region, expected_ids in EXPECTED_MEMBERSHIP.items():
        actual_ids = {hotel.id for hotel in catalogue.hotels_in(region)}
        assert actual_ids == expected_ids

    assert catalogue.supported_regions() == list(TripRegion)

    # Every hotel belongs to exactly one region, and none is left out.
    assert sum(len(ids) for ids in EXPECTED_MEMBERSHIP.values()) == 12


def test_kenya_and_tanzania_share_east_africa():
    countries = {
        hotel.country
        for hotel in catalogue.hotels_in(TripRegion.EAST_AFRICA)
    }
    assert countries == {"Kenya", "Tanzania"}


def test_unmapped_country_raises():
    with pytest.raises(UnknownCountryError) as excinfo:
        catalogue._build([_record("France")])

    assert "France" in str(excinfo.value)
    assert "test-hotel" in str(excinfo.value)
