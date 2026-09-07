"""Planner behaviour, with the Anthropic client stubbed.

No test here touches the network or needs an API key. What is asserted is
the control flow around the model: what reaches the prompt, how many calls
are made, and what happens when the model returns something unusable.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import anthropic
import httpx
import pytest

from app import planner
from app.planner import PlannerInvalidOutput, PlannerUnavailable, PlannerResponse
from app.schemas import PlannedOutput, UnsupportedOutput

CAPE_TOWN = "ellerman-house-cape-town"
STELLENBOSCH = "delaire-graff-stellenbosch"
LONDOLOZI = "londolozi-sabi-sand"

BRIEF = "10 days in South Africa for our anniversary."


def _planned(stops: List[Dict[str, Any]], value: int = 10, unit: str = "days") -> Dict:
    return {
        "status": "planned",
        "interpreted_brief": "10 days in South Africa, anniversary.",
        "trip_region": "south-africa",
        "trip_length": {"value": value, "unit": unit},
        "narrative": "Cape Town, the winelands, then the Sabi Sand.",
        "stops": stops,
    }


def _stop(hotel_id: str, nights: int) -> Dict[str, Any]:
    return {"hotel_id": hotel_id, "nights": nights, "rationale": "Because."}


VALID = _planned(
    [_stop(CAPE_TOWN, 3), _stop(STELLENBOSCH, 2), _stop(LONDOLOZI, 4)]
)

UNSUPPORTED = {
    "status": "unsupported",
    "interpreted_brief": "A week in Portugal.",
    "reason": "PIXI's catalogue does not cover Portugal.",
    "suggested_regions": ["italy"],
}


class _Response:
    def __init__(self, payload: Optional[Dict[str, Any]]) -> None:
        self.parsed_output = (
            None if payload is None else PlannerResponse(result=payload)
        )


class _Messages:
    def __init__(self, outcomes: List[Any]) -> None:
        self._outcomes = list(outcomes)
        self.calls: List[Dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> _Response:
        self.calls.append(kwargs)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return _Response(outcome)


class _Client:
    """Stands in for anthropic.Anthropic. Returns queued outcomes in order."""

    def __init__(self, *outcomes: Any) -> None:
        self.messages = _Messages(list(outcomes))


def _prompt_of(call: Dict[str, Any]) -> str:
    return call["messages"][0]["content"]


# --- the catalogue payload -------------------------------------------------


def test_every_hotel_reaches_the_prompt():
    payload = planner._catalogue_payload()
    assert len(payload) == 12
    assert {record["id"] for record in payload} == {
        hotel.id for hotel in planner.catalogue.all_hotels()
    }


def test_access_notes_are_supplied_to_the_model():
    payload = {record["id"]: record for record in planner._catalogue_payload()}
    # Pacing signal the model cannot recover from the description alone.
    assert "Not road-accessible" in payload["singita-grumeti"]["access_notes"]


def test_payload_omits_fields_that_inform_no_decision():
    record = planner._catalogue_payload()[0]
    for field in ("images", "rooms", "latitude", "longitude"):
        assert field not in record


def test_system_prompt_carries_the_catalogue_and_the_regions():
    system = planner._system_prompt()
    assert LONDOLOZI in system
    assert "south-africa" in system and "east-africa" in system


# --- the happy paths -------------------------------------------------------


def test_a_valid_plan_is_returned_after_one_call():
    client = _Client(VALID)
    result = planner.plan(BRIEF, client=client)

    assert isinstance(result, PlannedOutput)
    assert [stop.hotel_id for stop in result.stops] == [
        CAPE_TOWN,
        STELLENBOSCH,
        LONDOLOZI,
    ]
    assert len(client.messages.calls) == 1
    assert _prompt_of(client.messages.calls[0]) == BRIEF


def test_an_unsupported_brief_is_returned_not_repaired():
    client = _Client(UNSUPPORTED)
    result = planner.plan("A week in Portugal.", client=client)

    assert isinstance(result, UnsupportedOutput)
    assert len(client.messages.calls) == 1


# --- repair ----------------------------------------------------------------


def test_an_invalid_plan_is_repaired_once():
    broken = _planned([_stop("four-seasons-cape-town", 9)])
    client = _Client(broken, VALID)

    result = planner.plan(BRIEF, client=client)

    assert isinstance(result, PlannedOutput)
    assert len(client.messages.calls) == 2


def test_the_repair_prompt_names_the_problem():
    broken = _planned([_stop("four-seasons-cape-town", 9)])
    client = _Client(broken, VALID)
    planner.plan(BRIEF, client=client)

    repair = _prompt_of(client.messages.calls[1])
    assert "four-seasons-cape-town" in repair
    assert "not in the catalogue" in repair
    assert BRIEF in repair


def test_nights_that_do_not_sum_are_sent_to_repair():
    broken = _planned([_stop(CAPE_TOWN, 3), _stop(LONDOLOZI, 3)])  # 6, needs 9
    client = _Client(broken, VALID)
    planner.plan(BRIEF, client=client)

    assert "stop nights sum to 6" in _prompt_of(client.messages.calls[1])


def test_two_bad_plans_raise_rather_than_returning_something_wrong():
    broken = _planned([_stop("four-seasons-cape-town", 9)])
    client = _Client(broken, broken)

    with pytest.raises(PlannerInvalidOutput) as excinfo:
        planner.plan(BRIEF, client=client)

    assert len(client.messages.calls) == 2
    assert any("four-seasons" in problem for problem in excinfo.value.problems)


def test_repair_may_conclude_the_brief_is_unsupported():
    broken = _planned([_stop("four-seasons-cape-town", 9)])
    client = _Client(broken, UNSUPPORTED)

    assert isinstance(planner.plan(BRIEF, client=client), UnsupportedOutput)


# --- transport failures ----------------------------------------------------


def _api_error(status: int) -> anthropic.APIStatusError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status, request=request)
    return anthropic.APIStatusError("boom", response=response, body=None)


def test_a_connection_failure_is_not_repaired():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    client = _Client(anthropic.APIConnectionError(request=request))

    with pytest.raises(PlannerUnavailable) as excinfo:
        planner.plan(BRIEF, client=client)

    # The model never answered, so there is nothing to repair.
    assert len(client.messages.calls) == 1
    assert excinfo.value.retryable is True


def test_a_server_error_is_retryable():
    client = _Client(_api_error(503))
    with pytest.raises(PlannerUnavailable) as excinfo:
        planner.plan(BRIEF, client=client)
    assert excinfo.value.retryable is True


def test_a_client_error_is_not_retryable():
    client = _Client(_api_error(400))
    with pytest.raises(PlannerUnavailable) as excinfo:
        planner.plan(BRIEF, client=client)
    assert excinfo.value.retryable is False


def test_an_unparseable_response_is_repaired_then_raises():
    client = _Client(None, None)

    with pytest.raises(PlannerInvalidOutput):
        planner.plan(BRIEF, client=client)

    assert len(client.messages.calls) == 2


# --- the boundary that matters --------------------------------------------


def test_the_planner_schema_refuses_a_price():
    priced = _planned([_stop(CAPE_TOWN, 9)])
    priced["accommodation_total"] = 14200

    with pytest.raises(Exception):
        PlannerResponse(result=priced)


# --- the captured live response --------------------------------------------


def test_the_captured_live_response_still_validates():
    """A real Opus 5 response, captured 2026-09-07 from the worked-example brief.

    It exists so the frontend can be built without a key or a live call, and
    so a schema change that would break real model output fails here rather
    than in a demo. It is test and development data only — no production code
    path reads it.
    """
    import pathlib

    from app import itinerary

    path = pathlib.Path(__file__).parent / "fixtures"
    payload = json.loads(
        (path / "south_africa_anniversary_planned.json").read_text(encoding="utf-8")
    )

    parsed = PlannerResponse(result=payload).result
    assert isinstance(parsed, PlannedOutput)

    # Still domain-valid, not merely well-shaped.
    assert itinerary.validate_plan(parsed) == []
    assert [stop.hotel_id for stop in parsed.stops] == [
        CAPE_TOWN,
        STELLENBOSCH,
        LONDOLOZI,
    ]
    assert (parsed.trip_length.value, parsed.trip_length.unit) == (10, "days")
