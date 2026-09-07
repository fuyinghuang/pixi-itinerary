"""The supplied PIXI hotel catalogue, loaded once and queried in memory.

This is the only module that reads `data/hotels.json`. The dataset is
read-only and is the source of truth for every hotel fact, so nothing here
validates it — `data/validate.py` owns that.

`trip_region` is a product grouping used for itinerary coherence. It is
deliberately distinct from a hotel's `region` field, which is sub-national
("Western Cape", "Kanto").
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "hotels.json"


class TripRegion(str, Enum):
    """The regions an itinerary can be built in."""

    SOUTH_AFRICA = "south-africa"
    EAST_AFRICA = "east-africa"
    JAPAN = "japan"
    ITALY = "italy"


#: The dataset has no trip-region field, so the grouping is stated explicitly.
#: Kenya and Tanzania pair as one cross-border circuit.
COUNTRY_TO_TRIP_REGION: Dict[str, TripRegion] = {
    "South Africa": TripRegion.SOUTH_AFRICA,
    "Kenya": TripRegion.EAST_AFRICA,
    "Tanzania": TripRegion.EAST_AFRICA,
    "Japan": TripRegion.JAPAN,
    "Italy": TripRegion.ITALY,
}


class UnknownCountryError(ValueError):
    """A supplied country has no trip_region — fail loudly, never drop it."""


@dataclass(frozen=True)
class Airport:
    iata: str
    name: str


@dataclass(frozen=True)
class Room:
    name: str
    rate_delta: int


@dataclass(frozen=True)
class Hotel:
    """One property, exactly as supplied. See data/schema.md.

    Sequence fields are tuples so the shared catalogue cannot be mutated by
    a caller.
    """

    id: str
    name: str
    brand: Optional[str]
    country: str
    region: str  # sub-national — not TripRegion
    city: str
    latitude: float
    longitude: float
    nearest_airport: Airport
    description: str
    tags: Tuple[str, ...]
    approx_nightly_rate: int
    currency: str
    images: Tuple[str, ...]
    rooms: Tuple[Room, ...]
    access_notes: Optional[str] = None


def _to_hotel(record: Mapping[str, Any]) -> Hotel:
    return Hotel(
        id=record["id"],
        name=record["name"],
        brand=record["brand"],
        country=record["country"],
        region=record["region"],
        city=record["city"],
        latitude=record["latitude"],
        longitude=record["longitude"],
        nearest_airport=Airport(**record["nearest_airport"]),
        description=record["description"],
        tags=tuple(record["tags"]),
        approx_nightly_rate=record["approx_nightly_rate"],
        currency=record["currency"],
        images=tuple(record["images"]),
        rooms=tuple(Room(**room) for room in record["rooms"]),
        access_notes=record.get("access_notes"),
    )


def _build(records: Iterable[Mapping[str, Any]]) -> Dict[str, Hotel]:
    """Build the id -> Hotel index. Raises on a country we cannot place."""
    hotels: Dict[str, Hotel] = {}
    for record in records:
        hotel = _to_hotel(record)
        if hotel.country not in COUNTRY_TO_TRIP_REGION:
            raise UnknownCountryError(
                "{}: country {!r} has no trip_region".format(
                    hotel.id, hotel.country
                )
            )
        hotels[hotel.id] = hotel
    return hotels


def _load(path: Path = DATA_PATH) -> Dict[str, Hotel]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return _build(raw["hotels"])


#: Loaded once at import. A catalogue that cannot load is not a condition to
#: degrade around, so failures here are raised rather than swallowed.
_HOTELS: Dict[str, Hotel] = _load()


def all_hotels() -> List[Hotel]:
    """Every hotel, in dataset order."""
    return list(_HOTELS.values())


def get(hotel_id: str) -> Optional[Hotel]:
    """The hotel with this id, or None. Never raises on an unknown id."""
    return _HOTELS.get(hotel_id)


def trip_region_of(hotel: Hotel) -> TripRegion:
    """The trip_region a hotel belongs to."""
    return COUNTRY_TO_TRIP_REGION[hotel.country]


def hotels_in(region: TripRegion) -> List[Hotel]:
    """Every hotel in one trip_region, in dataset order."""
    return [h for h in _HOTELS.values() if trip_region_of(h) is region]


def supported_regions() -> List[TripRegion]:
    """The regions that actually have properties behind them."""
    return [region for region in TripRegion if hotels_in(region)]
