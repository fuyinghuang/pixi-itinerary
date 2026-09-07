"""The HTTP surface. No network, no API key.

The recompute route is exercised end to end because it is fully
deterministic. The generation route is exercised only where it does not
call the model: its planner is replaced.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from app import planner
from app.main import app
from app.schemas import PlannedOutput, UnsupportedOutput

client = TestClient(app)

CAPE_TOWN = "ellerman-house-cape-town"
STELLENBOSCH = "delaire-graff-stellenbosch"
LONDOLOZI = "londolozi-sabi-sand"


def _recompute_body(stops: List[Dict[str, Any]], unit: str = "days") -> Dict[str, Any]:
    return {
        "trip_region": "south-africa",
        "trip_length_unit": unit,
        "interpreted_brief": "10 days in South Africa.",
        "narrative": "Cape Town, winelands, safari.",
        "stops": stops,
    }


def _stop(hotel_id: str, nights: int) -> Dict[str, Any]:
    return {"hotel_id": hotel_id, "nights": nights, "rationale": "Because."}


# --- health ---------------------------------------------------------------


def test_health_reports_the_catalogue():
    body = client.get("/api/health").json()
    assert body["hotels"] == 12
    assert body["regions"] == ["south-africa", "east-africa", "japan", "italy"]


# --- recompute: fully deterministic, no stubbing --------------------------


def test_recompute_returns_a_priced_itinerary():
    response = client.post(
        "/api/itineraries/recompute",
        json=_recompute_body([_stop(CAPE_TOWN, 3), _stop(LONDOLOZI, 4)]),
    )
    assert response.status_code == 200

    body = response.json()
    assert body["accommodation_nights"] == 7
    assert body["total_days"] == 8
    assert body["currency"] == "USD"
    assert [stop["hotel"]["id"] for stop in body["stops"]] == [CAPE_TOWN, LONDOLOZI]
    assert body["accommodation_total"] == sum(s["subtotal"] for s in body["stops"])


def test_recompute_embeds_the_supplied_hotel_content():
    response = client.post(
        "/api/itineraries/recompute", json=_recompute_body([_stop(LONDOLOZI, 5)])
    )
    hotel = response.json()["stops"][0]["hotel"]

    assert len(hotel["images"]) == 5
    assert "access_notes" in hotel and hotel["access_notes"]
    assert hotel["nearest_airport"]["iata"] == "JNB"


def test_recompute_rejects_a_derived_field():
    body = _recompute_body([_stop(CAPE_TOWN, 3)])
    body["accommodation_total"] = 999
    assert client.post("/api/itineraries/recompute", json=body).status_code == 422


def test_recompute_reports_a_domain_violation():
    body = _recompute_body([_stop(CAPE_TOWN, 3), _stop(CAPE_TOWN, 3)])
    response = client.post("/api/itineraries/recompute", json=body)

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


# --- generation: planner replaced -----------------------------------------


@pytest.fixture
def stub_planner(monkeypatch):
    def _install(outcome):
        def fake_plan(brief: str, **kwargs: Any):
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        monkeypatch.setattr("app.main.planner.plan", fake_plan)

    return _install


def test_generation_returns_an_itinerary(stub_planner):
    stub_planner(
        PlannedOutput(
            status="planned",
            interpreted_brief="10 days in South Africa.",
            trip_region="south-africa",
            trip_length={"value": 10, "unit": "days"},
            narrative="Cape Town, winelands, safari.",
            stops=[
                _stop(CAPE_TOWN, 3),
                _stop(STELLENBOSCH, 2),
                _stop(LONDOLOZI, 4),
            ],
        )
    )
    response = client.post("/api/itineraries", json={"brief": "10 days in SA."})

    assert response.status_code == 200
    assert response.json()["accommodation_nights"] == 9


def test_an_unsupported_brief_is_a_success_not_an_error(stub_planner):
    stub_planner(
        UnsupportedOutput(
            status="unsupported",
            interpreted_brief="A week in Portugal.",
            reason="The catalogue does not cover Portugal.",
            suggested_regions=["italy"],
        )
    )
    response = client.post("/api/itineraries", json={"brief": "A week in Portugal."})

    assert response.status_code == 200
    body = response.json()
    assert body["suggested_regions"] == ["italy"]
    # Authoritative, from the catalogue rather than the model.
    assert body["supported_regions"] == [
        "south-africa",
        "east-africa",
        "japan",
        "italy",
    ]


def test_an_unreachable_planner_is_retryable(stub_planner):
    stub_planner(planner.PlannerUnavailable("unreachable", retryable=True))
    response = client.post("/api/itineraries", json={"brief": "10 days in SA."})

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "planner_unavailable"
    assert body["retryable"] is True


def test_unusable_output_reports_a_distinct_code(stub_planner):
    stub_planner(planner.PlannerInvalidOutput("no good", ["unknown hotel"]))
    response = client.post("/api/itineraries", json={"brief": "10 days in SA."})

    assert response.status_code == 503
    assert response.json()["code"] == "planner_invalid_output"


def test_an_empty_brief_is_rejected_before_the_model():
    assert client.post("/api/itineraries", json={"brief": ""}).status_code == 422
