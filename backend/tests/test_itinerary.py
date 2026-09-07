"""Deterministic itinerary logic: normalisation, validation, construction.

Field-level constraints (nights >= 1, at least one stop, trip-length bounds)
belong to the schemas and are tested there, not repeated here.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

import pytest

from app import catalogue, itinerary
from app.catalogue import TripRegion
from app.itinerary import InvalidPlanError, ViolationCode
from app.schemas import PlannedOutput, RecomputeRequest, TripLength

CAPE_TOWN = "ellerman-house-cape-town"
STELLENBOSCH = "delaire-graff-stellenbosch"
LONDOLOZI = "londolozi-sabi-sand"
ROME = "hotel-de-russie-rome"
RAVELLO = "belmond-caruso-ravello"
TOKYO = "aman-tokyo"


def _plan(
    stops: Sequence[Tuple[str, int]],
    *,
    value: int = 10,
    unit: str = "days",
    region: str = "south-africa",
) -> PlannedOutput:
    return PlannedOutput(
        status="planned",
        interpreted_brief="A trip.",
        trip_region=region,
        trip_length={"value": value, "unit": unit},
        narrative="A narrative.",
        stops=[
            {"hotel_id": hotel_id, "nights": nights, "rationale": "Because."}
            for hotel_id, nights in stops
        ],
    )


def _recompute(
    stops: Sequence[Tuple[str, int]],
    *,
    unit: str = "days",
    region: str = "south-africa",
) -> RecomputeRequest:
    return RecomputeRequest(
        trip_region=region,
        trip_length_unit=unit,
        interpreted_brief="A trip.",
        narrative="A narrative.",
        stops=[
            {"hotel_id": hotel_id, "nights": nights, "rationale": "Because."}
            for hotel_id, nights in stops
        ],
    )


def _codes(violations: List[itinerary.Violation]) -> List[ViolationCode]:
    return [violation.code for violation in violations]


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------


def test_ten_days_is_nine_nights():
    length = TripLength(value=10, unit="days")
    assert itinerary.accommodation_nights(length) == 9
    assert itinerary.total_days(9) == 10


def test_seven_nights_is_seven_nights():
    length = TripLength(value=7, unit="nights")
    assert itinerary.accommodation_nights(length) == 7
    assert itinerary.total_days(7) == 8


def test_shortest_trip():
    assert itinerary.accommodation_nights(TripLength(value=2, unit="days")) == 1
    assert itinerary.total_days(1) == 2


def test_normalisation_does_not_mutate_the_input():
    length = TripLength(value=10, unit="days")
    itinerary.accommodation_nights(length)
    assert (length.value, length.unit) == (10, "days")


# --------------------------------------------------------------------------
# validate_plan
# --------------------------------------------------------------------------


def test_valid_plan_has_no_violations():
    plan = _plan([(CAPE_TOWN, 3), (STELLENBOSCH, 2), (LONDOLOZI, 4)])
    assert itinerary.validate_plan(plan) == []


def test_unknown_hotel_is_reported():
    plan = _plan([(CAPE_TOWN, 5), ("four-seasons-cape-town", 4)])
    violations = itinerary.validate_plan(plan)
    assert _codes(violations) == [ViolationCode.UNKNOWN_HOTEL]
    assert "four-seasons-cape-town" in violations[0].message
    # The repair attempt needs to know what is actually available.
    assert LONDOLOZI in violations[0].message


def test_every_unknown_hotel_is_reported_not_just_the_first():
    plan = _plan([("nope-one", 5), ("nope-two", 4)])
    violations = itinerary.validate_plan(plan)
    assert _codes(violations).count(ViolationCode.UNKNOWN_HOTEL) == 2


def test_duplicate_hotel_is_reported_once():
    plan = _plan([(CAPE_TOWN, 3), (CAPE_TOWN, 3), (LONDOLOZI, 3)])
    assert _codes(itinerary.validate_plan(plan)) == [ViolationCode.DUPLICATE_HOTEL]


def test_hotel_from_another_region_is_reported():
    plan = _plan([(CAPE_TOWN, 5), (TOKYO, 4)])
    violations = itinerary.validate_plan(plan)
    assert _codes(violations) == [ViolationCode.REGION_MISMATCH]
    assert "japan" in violations[0].message


def test_nights_that_do_not_sum_are_reported():
    plan = _plan([(CAPE_TOWN, 3), (LONDOLOZI, 3)])  # 6, needs 9
    violations = itinerary.validate_plan(plan)
    assert _codes(violations) == [ViolationCode.NIGHTS_TOTAL_MISMATCH]
    assert "6" in violations[0].message and "9" in violations[0].message


def test_nights_mismatch_explains_when_the_trip_is_too_short_for_the_stops():
    plan = _plan([(CAPE_TOWN, 1), (STELLENBOSCH, 1)], value=2, unit="days")
    violations = itinerary.validate_plan(plan)
    assert _codes(violations) == [ViolationCode.NIGHTS_TOTAL_MISMATCH]
    assert "cannot cover" in violations[0].message


def test_more_stops_than_the_region_has_properties():
    # Italy has two. A third stop is necessarily from elsewhere, so the
    # capacity violation is reported alongside the region mismatch.
    plan = _plan(
        [(ROME, 3), (RAVELLO, 3), (TOKYO, 3)], value=9, unit="nights", region="italy"
    )
    codes = _codes(itinerary.validate_plan(plan))
    assert ViolationCode.TOO_MANY_STOPS in codes
    assert ViolationCode.REGION_MISMATCH in codes


def test_all_violations_are_collected_in_a_stable_order():
    plan = _plan([("nope", 3), (CAPE_TOWN, 3), (CAPE_TOWN, 3), (TOKYO, 3)])
    assert _codes(itinerary.validate_plan(plan)) == [
        ViolationCode.UNKNOWN_HOTEL,
        ViolationCode.DUPLICATE_HOTEL,
        ViolationCode.REGION_MISMATCH,
        ViolationCode.NIGHTS_TOTAL_MISMATCH,
    ]


# --------------------------------------------------------------------------
# validate_recompute
# --------------------------------------------------------------------------


def test_valid_recompute_has_no_violations():
    assert itinerary.validate_recompute(_recompute([(CAPE_TOWN, 4)])) == []


def test_recompute_does_not_check_a_nights_total():
    # The designer changing nights is allowed to change the trip length.
    assert itinerary.validate_recompute(_recompute([(CAPE_TOWN, 17)])) == []


def test_recompute_still_checks_the_catalogue():
    violations = itinerary.validate_recompute(_recompute([("nope", 3)]))
    assert _codes(violations) == [ViolationCode.UNKNOWN_HOTEL]


def test_recompute_days_boundary_is_valid_at_twenty_nine_nights():
    # 29 nights -> a 30-day trip, exactly at the maximum.
    request = _recompute([(ROME, 15), (RAVELLO, 14)], unit="days", region="italy")
    assert itinerary.validate_recompute(request) == []


def test_recompute_days_boundary_fails_at_thirty_nights():
    # 30 nights -> a 31-day trip, over the maximum.
    request = _recompute([(ROME, 15), (RAVELLO, 15)], unit="days", region="italy")
    violations = itinerary.validate_recompute(request)
    assert _codes(violations) == [ViolationCode.TRIP_LENGTH_OUT_OF_RANGE]
    assert "31-day" in violations[0].message


def test_recompute_nights_boundary_is_valid_at_thirty_nights():
    request = _recompute([(ROME, 15), (RAVELLO, 15)], unit="nights", region="italy")
    assert itinerary.validate_recompute(request) == []


def test_recompute_nights_boundary_fails_at_thirty_one_nights():
    request = _recompute([(ROME, 16), (RAVELLO, 15)], unit="nights", region="italy")
    violations = itinerary.validate_recompute(request)
    assert _codes(violations) == [ViolationCode.TRIP_LENGTH_OUT_OF_RANGE]
    assert "31-night" in violations[0].message


# --------------------------------------------------------------------------
# build_from_plan
# --------------------------------------------------------------------------


def test_day_ranges_are_contiguous_and_end_on_the_last_night():
    plan = _plan([(CAPE_TOWN, 3), (STELLENBOSCH, 2), (LONDOLOZI, 4)])
    built = itinerary.build_from_plan(plan)

    ranges = [(stop.day_from, stop.day_to) for stop in built.stops]
    assert ranges == [(1, 3), (4, 5), (6, 9)]
    assert built.accommodation_nights == 9
    assert built.total_days == 10
    # The final day is a departure day and belongs to no stop.
    assert built.stops[-1].day_to == built.accommodation_nights


def test_subtotal_is_nights_times_the_supplied_rate():
    plan = _plan([(CAPE_TOWN, 6), (LONDOLOZI, 3)])
    built = itinerary.build_from_plan(plan)

    londolozi = catalogue.get(LONDOLOZI)
    assert londolozi.approx_nightly_rate == 1800
    assert built.stops[1].subtotal == 3 * 1800


def test_total_is_the_sum_of_subtotals():
    plan = _plan([(CAPE_TOWN, 6), (LONDOLOZI, 3)])
    built = itinerary.build_from_plan(plan)
    assert built.accommodation_total == sum(s.subtotal for s in built.stops)


def test_currency_and_price_note_are_set():
    built = itinerary.build_from_plan(_plan([(CAPE_TOWN, 9)]))
    assert built.currency == "USD"
    assert "Flights, transfers and experiences are excluded" in built.price_note


def test_the_embedded_hotel_is_the_catalogue_record():
    built = itinerary.build_from_plan(_plan([(LONDOLOZI, 9)]))
    assert built.stops[0].hotel is catalogue.get(LONDOLOZI)


def test_replacement_options_exclude_every_used_hotel_and_stay_in_region():
    plan = _plan([(CAPE_TOWN, 5), (LONDOLOZI, 4)])
    built = itinerary.build_from_plan(plan)

    option_ids = {option.id for option in built.stops[0].replacement_options}
    assert option_ids == {STELLENBOSCH}


def test_replacement_options_are_empty_when_the_region_is_exhausted():
    plan = _plan([(ROME, 3), (RAVELLO, 3)], value=6, unit="nights", region="italy")
    built = itinerary.build_from_plan(plan)
    assert all(stop.replacement_options == [] for stop in built.stops)


def test_single_stop_of_one_night():
    plan = _plan([(CAPE_TOWN, 1)], value=2, unit="days")
    built = itinerary.build_from_plan(plan)

    assert (built.stops[0].day_from, built.stops[0].day_to) == (1, 1)
    assert built.accommodation_nights == 1
    assert built.total_days == 2


def test_build_refuses_an_invalid_plan():
    plan = _plan([(CAPE_TOWN, 3), (TOKYO, 6)])
    with pytest.raises(InvalidPlanError) as excinfo:
        itinerary.build_from_plan(plan)

    assert ViolationCode.REGION_MISMATCH in _codes(list(excinfo.value.violations))


# --------------------------------------------------------------------------
# build_from_recompute
# --------------------------------------------------------------------------


def test_recompute_builds_an_itinerary():
    built = itinerary.build_from_recompute(
        _recompute([(CAPE_TOWN, 3), (LONDOLOZI, 4)])
    )
    assert [stop.hotel.id for stop in built.stops] == [CAPE_TOWN, LONDOLOZI]
    assert built.accommodation_nights == 7


def test_adding_a_night_lengthens_a_day_stated_trip():
    built = itinerary.build_from_recompute(
        _recompute([(CAPE_TOWN, 4), (STELLENBOSCH, 2), (LONDOLOZI, 4)], unit="days")
    )
    assert built.accommodation_nights == 10
    assert built.trip_length.value == 11
    assert built.trip_length.unit == "days"


def test_a_night_stated_trip_keeps_its_unit():
    built = itinerary.build_from_recompute(
        _recompute([(CAPE_TOWN, 4), (LONDOLOZI, 3)], unit="nights")
    )
    assert built.trip_length.value == 7
    assert built.trip_length.unit == "nights"


def test_recompute_rebuilds_replacement_options_after_a_swap():
    before = itinerary.build_from_recompute(_recompute([(CAPE_TOWN, 5)]))
    assert {o.id for o in before.stops[0].replacement_options} == {
        STELLENBOSCH,
        LONDOLOZI,
    }

    after = itinerary.build_from_recompute(_recompute([(LONDOLOZI, 5)]))
    assert {o.id for o in after.stops[0].replacement_options} == {
        CAPE_TOWN,
        STELLENBOSCH,
    }


def test_recompute_refuses_an_invalid_edit():
    with pytest.raises(InvalidPlanError):
        itinerary.build_from_recompute(_recompute([(CAPE_TOWN, 3), (CAPE_TOWN, 3)]))
