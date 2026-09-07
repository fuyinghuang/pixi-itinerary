"""Deterministic itinerary logic.

Everything factual in an itinerary is computed here or read from the
supplied catalogue: trip-length normalisation, domain validation, day
ranges, pricing and replacement options. Nothing in this module calls an
LLM, reads the environment, or knows about HTTP.

Domain validation collects every violation rather than raising on the
first, because the planner gets a single repair attempt and must see all
the problems at once. Field-level constraints — nights at least one, at
least one stop, string lengths, trip-length bounds — belong to the Pydantic
schemas and are not rechecked here.

Invalid plans are never silently repaired. ``build_*`` raises rather than
adjusting numbers to make a plan fit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Sequence, Union

from app import catalogue
from app.catalogue import Hotel, TripRegion
from app.schemas import (
    MAX_TRIP_LENGTH,
    HotelOption,
    Itinerary,
    ItineraryStop,
    PlannedOutput,
    PlannerStop,
    RecomputeRequest,
    RecomputeStop,
    TripLength,
    TripLengthUnit,
)

#: A stop as it arrives from either path. Structurally identical.
StopInput = Union[PlannerStop, RecomputeStop]


class ViolationCode(str, Enum):
    """Domain rules a plan can break. Field-level rules are not here."""

    UNKNOWN_HOTEL = "unknown_hotel"
    DUPLICATE_HOTEL = "duplicate_hotel"
    REGION_MISMATCH = "region_mismatch"
    NIGHTS_TOTAL_MISMATCH = "nights_total_mismatch"
    TOO_MANY_STOPS = "too_many_stops"
    TRIP_LENGTH_OUT_OF_RANGE = "trip_length_out_of_range"


@dataclass(frozen=True)
class Violation:
    """One broken domain rule.

    ``message`` is written to be read by the model in the repair attempt,
    so it names the offending value and what would be acceptable.
    """

    code: ViolationCode
    message: str


class InvalidPlanError(Exception):
    """Raised when construction is attempted on a plan that does not validate."""

    def __init__(self, violations: Iterable[Violation]) -> None:
        self.violations = tuple(violations)
        super().__init__("; ".join(v.message for v in self.violations))


# --------------------------------------------------------------------------
# Trip-length normalisation
# --------------------------------------------------------------------------


def accommodation_nights(trip_length: TripLength) -> int:
    """Nights actually spent in hotels. Days and nights are never equated."""
    if trip_length.unit == "days":
        return trip_length.value - 1
    return trip_length.value


def total_days(nights: int) -> int:
    """Days the trip spans. The final day is a departure day with no stop."""
    return nights + 1


def _trip_length_value(nights: int, unit: TripLengthUnit) -> int:
    """The stated trip length that these accommodation nights imply."""
    if unit == "days":
        return nights + 1
    return nights


def _singular(unit: TripLengthUnit) -> str:
    return unit[:-1]


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def _shared_violations(
    trip_region: TripRegion, stops: Sequence[StopInput]
) -> List[Violation]:
    """Checks that apply to both generation and recompute, in a fixed order."""
    violations: List[Violation] = []
    available = catalogue.hotels_in(trip_region)
    valid_ids = [hotel.id for hotel in available]

    # 1. Every hotel_id exists in the supplied catalogue.
    for stop in stops:
        if catalogue.get(stop.hotel_id) is None:
            violations.append(
                Violation(
                    ViolationCode.UNKNOWN_HOTEL,
                    "'{}' is not in the catalogue. Valid ids for {}: {}".format(
                        stop.hotel_id, trip_region.value, ", ".join(valid_ids)
                    ),
                )
            )

    # 2. No property appears twice.
    seen = set()
    reported = set()
    for stop in stops:
        if stop.hotel_id in seen and stop.hotel_id not in reported:
            reported.add(stop.hotel_id)
            violations.append(
                Violation(
                    ViolationCode.DUPLICATE_HOTEL,
                    "'{}' appears more than once; every stop must be a "
                    "different property".format(stop.hotel_id),
                )
            )
        seen.add(stop.hotel_id)

    # 3. Every resolvable hotel belongs to the declared region.
    for stop in stops:
        hotel = catalogue.get(stop.hotel_id)
        if hotel is None:
            continue
        actual = catalogue.trip_region_of(hotel)
        if actual is not trip_region:
            violations.append(
                Violation(
                    ViolationCode.REGION_MISMATCH,
                    "'{}' is in {}, but this itinerary is {}".format(
                        hotel.id, actual.value, trip_region.value
                    ),
                )
            )

    # 4. The region has enough properties for the stops requested.
    unique_stops = len({stop.hotel_id for stop in stops})
    if unique_stops > len(available):
        violations.append(
            Violation(
                ViolationCode.TOO_MANY_STOPS,
                "{} stops requested but {} has only {} properties".format(
                    unique_stops, trip_region.value, len(available)
                ),
            )
        )

    return violations


def validate_plan(plan: PlannedOutput) -> List[Violation]:
    """Domain violations in a generated plan. Empty list means valid."""
    violations = _shared_violations(plan.trip_region, plan.stops)

    expected = accommodation_nights(plan.trip_length)
    actual = sum(stop.nights for stop in plan.stops)
    if actual != expected:
        message = (
            "stop nights sum to {} but a {}-{} brief allows {} accommodation "
            "nights".format(
                actual,
                plan.trip_length.value,
                _singular(plan.trip_length.unit),
                expected,
            )
        )
        if expected < len(plan.stops):
            message += " — {} nights cannot cover {} stops".format(
                expected, len(plan.stops)
            )
        violations.append(Violation(ViolationCode.NIGHTS_TOTAL_MISMATCH, message))

    return violations


def validate_recompute(request: RecomputeRequest) -> List[Violation]:
    """Domain violations in a designer edit. Empty list means valid.

    There is no nights-total check: editing a stop's nights is allowed to
    change the length of the trip. The derived length must still be within
    bounds, and the bound applies to the derived *stated* value, which
    depends on the unit — 30 accommodation nights is a valid 30-night trip
    but an invalid 31-day one.
    """
    violations = _shared_violations(request.trip_region, request.stops)

    nights = sum(stop.nights for stop in request.stops)
    value = _trip_length_value(nights, request.trip_length_unit)
    if value > MAX_TRIP_LENGTH:
        violations.append(
            Violation(
                ViolationCode.TRIP_LENGTH_OUT_OF_RANGE,
                "{} accommodation nights would make a {}-{} trip, above the "
                "{} maximum".format(
                    nights,
                    value,
                    _singular(request.trip_length_unit),
                    MAX_TRIP_LENGTH,
                ),
            )
        )

    return violations


# --------------------------------------------------------------------------
# Construction
# --------------------------------------------------------------------------


def _replacement_options(
    trip_region: TripRegion, stops: Sequence[StopInput]
) -> List[HotelOption]:
    """Properties in the same region that the itinerary is not already using.

    A stop's own hotel is excluded too — swapping a hotel for itself is not
    a swap. A region with no spare properties yields an empty list.
    """
    used = {stop.hotel_id for stop in stops}
    return [
        HotelOption(id=hotel.id, name=hotel.name, city=hotel.city)
        for hotel in catalogue.hotels_in(trip_region)
        if hotel.id not in used
    ]


def _hotel_for(stop: StopInput) -> Hotel:
    hotel = catalogue.get(stop.hotel_id)
    if hotel is None:  # pragma: no cover - validation runs first
        raise InvalidPlanError(
            [
                Violation(
                    ViolationCode.UNKNOWN_HOTEL,
                    "'{}' is not in the catalogue".format(stop.hotel_id),
                )
            ]
        )
    return hotel


def _assemble(
    interpreted_brief: str,
    narrative: str,
    trip_region: TripRegion,
    trip_length: TripLength,
    nights: int,
    stops: Sequence[StopInput],
) -> Itinerary:
    options = _replacement_options(trip_region, stops)

    itinerary_stops: List[ItineraryStop] = []
    cursor = 1
    for stop in stops:
        hotel = _hotel_for(stop)
        day_to = cursor + stop.nights - 1
        itinerary_stops.append(
            ItineraryStop(
                day_from=cursor,
                day_to=day_to,
                nights=stop.nights,
                rationale=stop.rationale,
                hotel=hotel,
                subtotal=stop.nights * hotel.approx_nightly_rate,
                replacement_options=options,
            )
        )
        cursor = day_to + 1

    return Itinerary(
        interpreted_brief=interpreted_brief,
        narrative=narrative,
        trip_region=trip_region,
        trip_length=trip_length,
        accommodation_nights=nights,
        total_days=total_days(nights),
        accommodation_total=sum(stop.subtotal for stop in itinerary_stops),
        stops=itinerary_stops,
    )


def build_from_plan(plan: PlannedOutput) -> Itinerary:
    """Build an itinerary from a generated plan, or raise with every violation."""
    violations = validate_plan(plan)
    if violations:
        raise InvalidPlanError(violations)

    return _assemble(
        interpreted_brief=plan.interpreted_brief,
        narrative=plan.narrative,
        trip_region=plan.trip_region,
        trip_length=plan.trip_length,
        nights=accommodation_nights(plan.trip_length),
        stops=plan.stops,
    )


def build_from_recompute(request: RecomputeRequest) -> Itinerary:
    """Rebuild an itinerary from a designer edit, or raise with every violation.

    The trip length is derived from the edited stop nights, keeping the unit
    the client originally stated.
    """
    violations = validate_recompute(request)
    if violations:
        raise InvalidPlanError(violations)

    nights = sum(stop.nights for stop in request.stops)
    trip_length = TripLength(
        value=_trip_length_value(nights, request.trip_length_unit),
        unit=request.trip_length_unit,
    )

    return _assemble(
        interpreted_brief=request.interpreted_brief,
        narrative=request.narrative,
        trip_region=request.trip_region,
        trip_length=trip_length,
        nights=nights,
        stops=request.stops,
    )
