"""The HTTP surface. Two routes, and nothing else.

Every decision lives upstream: ``planner`` owns the model call, ``itinerary``
owns validation and derivation, ``catalogue`` owns the supplied data. This
module translates between HTTP and those modules and does no work of its own.

An unsupported brief is a normal product outcome and returns 200 with a
typed response. Only a genuine failure — the model unreachable, or unusable
output after the single repair — returns an error status, and it is always
something the UI can render and retry.
"""

from __future__ import annotations

import os
from typing import Union

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import catalogue, itinerary, planner
from app.schemas import (
    BriefRequest,
    ErrorResponse,
    Itinerary,
    RecomputeRequest,
    UnsupportedBriefResponse,
)

load_dotenv()

#: Vite's dev server. Widened only when a deployed origin actually exists.
ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

app = FastAPI(title="PIXI Itinerary Builder", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _error(status: int, code: str, message: str, retryable: bool) -> JSONResponse:
    body = ErrorResponse(code=code, message=message, retryable=retryable)
    return JSONResponse(status_code=status, content=body.model_dump())


@app.get("/api/health")
def health() -> dict:
    """Enough to tell whether the catalogue loaded and a key is configured."""
    return {
        "status": "ok",
        "hotels": len(catalogue.all_hotels()),
        "regions": [region.value for region in catalogue.supported_regions()],
        "planner_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }


@app.post(
    "/api/itineraries",
    response_model=Union[Itinerary, UnsupportedBriefResponse],
)
def create_itinerary(request: BriefRequest):
    """Turn a client brief into an itinerary.

    Returns 200 with an itinerary, or 200 with an unsupported-brief response
    when the catalogue cannot serve the destination. Neither is an error.
    """
    try:
        proposal = planner.plan(request.brief)
    except planner.PlannerUnavailable as exc:
        return _error(503, "planner_unavailable", str(exc), exc.retryable)
    except planner.PlannerInvalidOutput as exc:
        return _error(503, "planner_invalid_output", str(exc), True)

    if proposal.status == "unsupported":
        return UnsupportedBriefResponse(
            interpreted_brief=proposal.interpreted_brief,
            reason=proposal.reason,
            suggested_regions=proposal.suggested_regions,
            supported_regions=catalogue.supported_regions(),
        )

    # The planner has already validated this, so a failure here is a bug.
    return itinerary.build_from_plan(proposal)


@app.post("/api/itineraries/recompute", response_model=Itinerary)
def recompute_itinerary(request: RecomputeRequest):
    """Rebuild an itinerary after a designer edit. No model call."""
    try:
        return itinerary.build_from_recompute(request)
    except itinerary.InvalidPlanError as exc:
        return _error(
            422,
            "invalid_request",
            "; ".join(violation.message for violation in exc.violations),
            False,
        )
