"""Contract constraints that carry product meaning.

Chiefly: the planner schema must make it impossible for the model to author
a derived fact. That is a claim the architecture rests on, so it is asserted
rather than assumed.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest
from pydantic import TypeAdapter, ValidationError

from app.catalogue import TripRegion
from app.schemas import (
    BriefRequest,
    PlannedOutput,
    PlannerOutput,
    RecomputeRequest,
    TripLength,
    UnsupportedOutput,
)

planner_adapter = TypeAdapter(PlannerOutput)


def _planned(**overrides: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": "planned",
        "interpreted_brief": "10 days in South Africa for an anniversary.",
        "trip_region": "south-africa",
        "trip_length": {"value": 10, "unit": "days"},
        "narrative": "Cape Town, the winelands, then the Sabi Sand.",
        "stops": [
            {
                "hotel_id": "ellerman-house-cape-town",
                "nights": 9,
                "rationale": "A quiet start above the Atlantic.",
            }
        ],
    }
    payload.update(overrides)
    return payload


# --- trip length ----------------------------------------------------------


def test_days_must_be_at_least_two():
    # One day normalises to zero accommodation nights.
    with pytest.raises(ValidationError):
        TripLength(value=1, unit="days")

    assert TripLength(value=2, unit="days").value == 2


def test_one_night_is_valid():
    assert TripLength(value=1, unit="nights").unit == "nights"


def test_trip_length_has_an_upper_bound():
    with pytest.raises(ValidationError):
        TripLength(value=31, unit="nights")


def test_unit_is_preserved_not_normalised():
    length = TripLength(value=10, unit="days")
    assert (length.value, length.unit) == (10, "days")


# --- the planner cannot author derived facts ------------------------------


@pytest.mark.parametrize(
    "forbidden",
    [
        {"accommodation_total": 14200},
        {"total_price": 14200},
        {"distance_km": 210},
        {"transfer_duration_minutes": 45},
    ],
)
def test_planner_output_rejects_derived_fields(forbidden: Dict[str, Any]):
    with pytest.raises(ValidationError):
        PlannedOutput(**_planned(**forbidden))


def test_planner_stop_rejects_derived_fields():
    payload = _planned()
    payload["stops"][0]["subtotal"] = 5850
    with pytest.raises(ValidationError):
        PlannedOutput(**payload)


def test_planner_stop_requires_at_least_one_night():
    payload = _planned()
    payload["stops"][0]["nights"] = 0
    with pytest.raises(ValidationError):
        PlannedOutput(**payload)


def test_planned_output_needs_at_least_one_stop():
    with pytest.raises(ValidationError):
        PlannedOutput(**_planned(stops=[]))


# --- discriminated union --------------------------------------------------


def test_union_selects_planned():
    parsed = planner_adapter.validate_python(_planned())
    assert isinstance(parsed, PlannedOutput)
    assert parsed.trip_region is TripRegion.SOUTH_AFRICA


def test_union_selects_unsupported():
    parsed = planner_adapter.validate_python(
        {
            "status": "unsupported",
            "interpreted_brief": "A week in Portugal.",
            "reason": "The catalogue does not cover Portugal.",
            "suggested_regions": ["italy"],
        }
    )
    assert isinstance(parsed, UnsupportedOutput)


def test_suggested_regions_may_be_empty():
    parsed = UnsupportedOutput(
        status="unsupported",
        interpreted_brief="Somewhere warm.",
        reason="Too little to place a region.",
    )
    assert parsed.suggested_regions == []


# --- requests -------------------------------------------------------------


def test_brief_must_not_be_empty():
    with pytest.raises(ValidationError):
        BriefRequest(brief="")


def test_brief_is_length_capped():
    with pytest.raises(ValidationError):
        BriefRequest(brief="x" * 2001)


def _recompute_payload() -> Dict[str, Any]:
    return {
        "trip_region": "italy",
        "trip_length_unit": "nights",
        "interpreted_brief": "Five nights in Italy.",
        "narrative": "Rome, then the Amalfi coast.",
        "stops": [
            {
                "hotel_id": "hotel-de-russie-rome",
                "nights": 5,
                "rationale": "Central, with a garden.",
            }
        ],
    }


def test_recompute_accepts_only_editable_fields():
    assert RecomputeRequest(**_recompute_payload()).stops[0].nights == 5


def test_recompute_rejects_derived_and_dataset_fields():
    payload = _recompute_payload()
    payload["accommodation_total"] = 4000
    with pytest.raises(ValidationError):
        RecomputeRequest(**payload)


def test_recompute_rejects_a_stale_trip_length():
    # The trip length is derived from the edited stop nights, so a client
    # sending a value would be sending something the backend must ignore.
    payload = _recompute_payload()
    payload["trip_length"] = {"value": 5, "unit": "nights"}
    with pytest.raises(ValidationError):
        RecomputeRequest(**payload)


def test_recompute_requires_a_trip_length_unit():
    payload = _recompute_payload()
    del payload["trip_length_unit"]
    with pytest.raises(ValidationError):
        RecomputeRequest(**payload)
