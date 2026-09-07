"""The single LLM call that turns a client brief into a proposed itinerary.

This is the only module that talks to Anthropic or reads the API key.

The model owns judgement and language: interpreting the brief, selecting
properties, sequencing them, allocating nights, and writing the rationale
and narrative. It owns no derived facts — the response schema has no price,
distance or travel-duration field, so a model that emits one fails
validation rather than having the field silently dropped.

`access_notes` is supplied to the model as dataset-owned factual input, so
it can pace a trip realistically — a fly-in camp is not a one-night stop.
The model may paraphrase it, but must not introduce transfer specifics the
field does not contain, and must not derive a route, distance, duration,
transport mode or feasibility from anything.

Invalid output gets one repair attempt. There is no fixture fallback: if
the model cannot produce a usable plan, the caller gets an error to render,
never a canned response presented as generated.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

import anthropic
from pydantic import BaseModel, ValidationError

from app import catalogue, itinerary
from app.schemas import PlannedOutput, PlannerOutput, UnsupportedOutput

MODEL = "claude-opus-5"
MAX_TOKENS = 8000

#: Fields the model needs to judge with. Images, rooms and coordinates are
#: omitted: they inform no planning decision and only cost tokens.
CATALOGUE_FIELDS = (
    "id",
    "name",
    "country",
    "region",
    "city",
    "tags",
    "description",
    "approx_nightly_rate",
)


class PlannerResponse(BaseModel):
    """Transport wrapper.

    The structured-output schema needs an object at the root, and
    ``PlannerOutput`` is a discriminated union. Internal to this module.
    """

    result: PlannerOutput


class PlannerUnavailable(Exception):
    """The model could not be reached, or refused the request."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class PlannerInvalidOutput(Exception):
    """The model produced an unusable plan, and the repair attempt failed."""

    def __init__(self, message: str, problems: List[str]) -> None:
        super().__init__(message)
        self.problems = list(problems)


class _SchemaRejected(Exception):
    """Internal: the response did not satisfy the planner schema."""


def _catalogue_payload() -> List[Dict[str, Any]]:
    """The catalogue as the model sees it. Supplied facts only."""
    payload = []
    for hotel in catalogue.all_hotels():
        record: Dict[str, Any] = {
            field: getattr(hotel, field) for field in CATALOGUE_FIELDS
        }
        record["tags"] = list(hotel.tags)
        record["trip_region"] = catalogue.trip_region_of(hotel).value
        record["nearest_airport"] = hotel.nearest_airport.iata
        record["access_notes"] = hotel.access_notes
        payload.append(record)
    return payload


def _system_prompt() -> str:
    regions = ", ".join(region.value for region in catalogue.supported_regions())
    return (
        "You are a travel designer's planning assistant at PIXI. A client "
        "brief arrives in the client's own words. You propose an itinerary "
        "drawn only from the catalogue below.\n"
        "\n"
        "What you decide:\n"
        "- which properties to use, in what order\n"
        "- how many nights at each\n"
        "- how you read the brief, and the copy that presents the trip\n"
        "\n"
        "Rules:\n"
        "- Use only hotel ids from the catalogue. Never invent a property.\n"
        "- Every stop must share one trip_region. The catalogue supports: "
        + regions
        + ".\n"
        "- A region has a fixed number of properties; you cannot use more "
        "stops than it has, and never the same property twice.\n"
        "- Read trip length from the brief and report it as the client "
        "stated it, in days or in nights. Do not convert between them.\n"
        "- Accommodation nights are the trip length minus one when stated "
        "in days, and the trip length when stated in nights. Your stop "
        "nights must sum to that.\n"
        "- Use access_notes to pace the trip. A property reached by light "
        "aircraft or boat rarely deserves a single night.\n"
        "- You may refer to how a guest reaches a property, but only using "
        "what access_notes actually says. Never state a duration, distance, "
        "transport mode or route that is not in the supplied text.\n"
        "- Never state a price, a total, or any calculated figure. Those are "
        "computed elsewhere.\n"
        "- If the brief asks for somewhere the catalogue cannot serve, "
        "return the unsupported result with a short honest reason and the "
        "regions that would suit the client instead. Do not substitute a "
        "different destination and present it as if it were requested.\n"
        "\n"
        "Catalogue:\n"
        + json.dumps(_catalogue_payload(), ensure_ascii=False, indent=None)
    )


def _repair_prompt(brief: str, previous: str, problems: List[str]) -> str:
    listed = "\n".join("- {}".format(problem) for problem in problems)
    return (
        "The brief was:\n{brief}\n\n"
        "You proposed:\n{previous}\n\n"
        "That proposal cannot be used. Every problem below must be fixed:\n"
        "{listed}\n\n"
        "Return a corrected proposal. Change only what the problems require."
    ).format(brief=brief, previous=previous, listed=listed)


def _call(client: Any, prompt: str) -> PlannerOutput:
    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=_system_prompt(),
            messages=[{"role": "user", "content": prompt}],
            output_format=PlannerResponse,
        )
    except anthropic.AuthenticationError as exc:
        raise PlannerUnavailable(
            "The itinerary service is not configured.", retryable=False
        ) from exc
    except anthropic.RateLimitError as exc:
        raise PlannerUnavailable(
            "The itinerary service is busy. Try again in a moment.",
            retryable=True,
        ) from exc
    except anthropic.APIStatusError as exc:
        raise PlannerUnavailable(
            "The itinerary service returned an error.",
            retryable=exc.status_code >= 500,
        ) from exc
    except anthropic.APIConnectionError as exc:
        raise PlannerUnavailable(
            "The itinerary service could not be reached.", retryable=True
        ) from exc

    parsed = response.parsed_output
    if parsed is None:
        raise _SchemaRejected("the response did not match the required shape")
    return parsed.result


def plan(brief: str, *, client: Optional[Any] = None) -> PlannerOutput:
    """Propose an itinerary for a brief, or report that it cannot be served.

    Returns a ``PlannedOutput`` that has passed domain validation, or an
    ``UnsupportedOutput`` when the catalogue cannot serve the brief.

    Raises ``PlannerUnavailable`` if the model could not be reached, or
    ``PlannerInvalidOutput`` if it produced an unusable plan twice.
    """
    if client is None:  # pragma: no cover - constructed only in the live path
        client = anthropic.Anthropic()

    previous: str
    problems: List[str]

    try:
        output = _call(client, brief)
    except _SchemaRejected as exc:
        previous = "(a response that did not match the required shape)"
        problems = [str(exc)]
    except ValidationError as exc:
        previous = "(a response that did not match the required shape)"
        problems = [str(exc)]
    else:
        if isinstance(output, UnsupportedOutput):
            return output

        violations = itinerary.validate_plan(output)
        if not violations:
            return output

        previous = output.model_dump_json()
        problems = [violation.message for violation in violations]

    # One repair attempt, then stop. Never silently accept a broken plan.
    try:
        repaired = _call(client, _repair_prompt(brief, previous, problems))
    except (_SchemaRejected, ValidationError) as exc:
        raise PlannerInvalidOutput(
            "The itinerary could not be generated.", problems + [str(exc)]
        ) from exc

    if isinstance(repaired, UnsupportedOutput):
        return repaired

    violations = itinerary.validate_plan(repaired)
    if violations:
        raise PlannerInvalidOutput(
            "The itinerary could not be generated.",
            [violation.message for violation in violations],
        )

    return repaired
