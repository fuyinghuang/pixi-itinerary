"""The canonical API contract.

Two boundaries live here and are deliberately kept apart:

* **Planner models** are internal. They carry only what the LLM is
  responsible for — interpretation, selection, sequencing, night allocation
  and language. They are never serialised to a client.
* **Response models** are public. Every factual or derived value in them
  comes from the supplied catalogue or from deterministic Python.

The planner models set ``extra="forbid"``, so a model that emits a price,
a total or a travel duration produces a validation error rather than having
the field silently dropped. That is the structural enforcement of the rule
that the LLM never authors derived facts.

Structural shape and field constraints are validated here. Catalogue ids,
region coherence, duplicates, nights arithmetic and stop limits belong to
``itinerary.py``, which collects them into a violation list for the single
repair attempt.
"""

from __future__ import annotations

from typing import Annotated, List, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.catalogue import Hotel, TripRegion

MAX_TRIP_LENGTH = 30

#: How the client stated the trip length. Preserved end to end so the brief
#: can be echoed back in the client's own terms.
TripLengthUnit = Literal["days", "nights"]

PRICE_NOTE = (
    "Indicative accommodation only, based on the base room category for one "
    "room. Flights, transfers and experiences are excluded."
)


# --------------------------------------------------------------------------
# Shared
# --------------------------------------------------------------------------


class TripLength(BaseModel):
    """Trip length as the client stated it.

    The value and unit are preserved rather than normalised here, so the
    brief can be echoed back accurately. Conversion to accommodation nights
    is deterministic and lives in ``itinerary.py``.
    """

    value: int = Field(ge=1, le=MAX_TRIP_LENGTH)
    unit: TripLengthUnit

    @model_validator(mode="after")
    def _days_need_at_least_two(self) -> "TripLength":
        # One day normalises to zero accommodation nights, which is not a trip.
        if self.unit == "days" and self.value < 2:
            raise ValueError("a trip stated in days must be at least 2 days")
        return self


# --------------------------------------------------------------------------
# Requests (public)
# --------------------------------------------------------------------------


class BriefRequest(BaseModel):
    """The client's own words, as pasted by the designer."""

    model_config = ConfigDict(str_strip_whitespace=True)

    brief: str = Field(min_length=1, max_length=2000)


class RecomputeStop(BaseModel):
    """One stop as edited by the designer."""

    hotel_id: str = Field(min_length=1)
    nights: int = Field(ge=1, le=MAX_TRIP_LENGTH)
    rationale: str = Field(max_length=600)


class RecomputeRequest(BaseModel):
    """A designer edit. Deterministic recomputation only — no LLM call.

    Only LLM-authored and editable fields are accepted. Prices, subtotals,
    day numbers, hotel content and replacement options are recomputed from
    the catalogue every time, so ``extra="forbid"`` rejects a client that
    tries to send them.

    The trip length is carried as a unit alone. Editing a stop's nights is
    allowed to change how long the trip is, so the new length is derived
    from the edited stop nights rather than trusted from the client — but
    the unit the client originally stated is preserved.
    """

    model_config = ConfigDict(extra="forbid")

    trip_region: TripRegion
    trip_length_unit: TripLengthUnit
    interpreted_brief: str = Field(max_length=300)
    narrative: str = Field(max_length=1200)
    stops: List[RecomputeStop] = Field(min_length=1)


# --------------------------------------------------------------------------
# Planner output (internal only)
# --------------------------------------------------------------------------


class PlannerStop(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hotel_id: str = Field(min_length=1)
    nights: int = Field(ge=1, le=MAX_TRIP_LENGTH)
    rationale: str = Field(max_length=600)


class PlannedOutput(BaseModel):
    """A proposed itinerary. Judgement and language only."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["planned"]
    interpreted_brief: str = Field(max_length=300)
    trip_region: TripRegion
    trip_length: TripLength
    narrative: str = Field(max_length=1200)
    stops: List[PlannerStop] = Field(min_length=1)


class UnsupportedOutput(BaseModel):
    """The catalogue cannot coherently serve this brief."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["unsupported"]
    interpreted_brief: str = Field(max_length=300)
    reason: str = Field(max_length=600)
    suggested_regions: List[TripRegion] = Field(default_factory=list, max_length=4)


PlannerOutput = Annotated[
    Union[PlannedOutput, UnsupportedOutput],
    Field(discriminator="status"),
]


# --------------------------------------------------------------------------
# Responses (public)
# --------------------------------------------------------------------------


class HotelOption(BaseModel):
    """A property the designer may swap in. Same trip_region, not already used."""

    id: str
    name: str
    city: str


class ItineraryStop(BaseModel):
    """One stop, with the hotel record embedded whole.

    ``hotel`` carries ``nearest_airport`` and ``access_notes`` as supplied.
    Nothing here derives a route, transport mode, duration or feasibility
    from them.
    """

    day_from: int = Field(ge=1)
    day_to: int = Field(ge=1)
    nights: int = Field(ge=1)
    rationale: str
    hotel: Hotel
    subtotal: int = Field(ge=0)
    replacement_options: List[HotelOption] = Field(default_factory=list)


class Itinerary(BaseModel):
    """The generated itinerary, and the result of every recompute."""

    interpreted_brief: str
    narrative: str
    trip_region: TripRegion
    trip_length: TripLength
    accommodation_nights: int = Field(ge=1)
    total_days: int = Field(ge=2)
    currency: Literal["USD"] = "USD"
    accommodation_total: int = Field(ge=0)
    price_note: str = PRICE_NOTE
    stops: List[ItineraryStop] = Field(min_length=1)


class UnsupportedBriefResponse(BaseModel):
    """A normal product outcome, returned with HTTP 200.

    ``suggested_regions`` is the model's judgement and may be empty;
    ``supported_regions`` is authoritative and comes from the catalogue.
    """

    interpreted_brief: str
    reason: str
    suggested_regions: List[TripRegion] = Field(default_factory=list)
    supported_regions: List[TripRegion]


class ErrorResponse(BaseModel):
    """A genuine failure, as opposed to an unsupported brief."""

    code: Literal[
        "planner_unavailable",
        "planner_invalid_output",
        "invalid_request",
    ]
    message: str
    retryable: bool
