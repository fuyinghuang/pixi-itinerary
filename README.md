# PIXI Itinerary Builder

Turns a travel designer's client brief into a sequenced, imagery-rich
luxury itinerary drawn from PIXI's supplied hotel catalogue.

Built for the PIXI AI Product Engineer take-home exercise. The product
reasoning — what was considered, what was chosen, and why — is in
[`docs/APPROACH.md`](docs/APPROACH.md). A running build journal is in
[`BUILD_LOG.md`](BUILD_LOG.md).

> **Status: generation works end to end.** A designer can paste a brief and
> get back a priced, image-led itinerary in the browser. Editing and the
> client preview are not built yet.

## What it does

A designer pastes the client's own words — *"10 days in South Africa for
our anniversary, a few days in Cape Town, some time in the winelands, then
safari to finish"* — and gets back a day-by-day itinerary they can adjust
and then present to the client.

Generation works today in the browser. Editing and the client preview are
not built yet.

The journey:

```text
client brief
  → the model proposes a grounded itinerary
  → deterministic validation and pricing
  → the designer reviews
  → change nights / replace a hotel
  → client-facing preview
```

The model handles judgement and language: interpreting the brief, choosing
properties, sequencing stops, allocating nights, and writing the rationale
and narrative. It may propose planning values such as nights per stop.

It does not author derived prices, distances, transfer durations, or
calculated totals. Those come from deterministic Python or directly from
supplied dataset fields, and every hotel referenced is validated against
the supplied catalogue. The boundary is enforced by the schema rather than
by instruction: the model's response has no field a price could occupy.

## Stack

- **Backend** — Python 3.9, FastAPI
- **Frontend** — React + TypeScript (Vite)
- **LLM** — Anthropic API
- **Data** — `data/hotels.json`, 12 luxury properties across five
  countries, supplied with the exercise and committed unmodified

The brief requires a Python backend and a React + TypeScript frontend.
FastAPI and Vite are our choices — see
[`docs/APPROACH.md`](docs/APPROACH.md).

## Prerequisites

- Python 3.9 or later
- Node 18 or later
- An Anthropic API key, for generating itineraries

## Setup

```bash
git clone <repo-url>
cd pixi-itinerary
cp .env.example .env
# open .env and set ANTHROPIC_API_KEY
```

### Dataset

The hotel data is committed to the repository — there is no download or
seed step. Verify it loads cleanly:

```bash
python3 data/validate.py
# expected: OK: 12 hotels across 5 countries — all valid.
```

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                                    # 88 tests
uvicorn app.main:app --reload             # http://localhost:8000
```

Check it came up, and that the catalogue loaded:

```bash
curl -s localhost:8000/api/health
# {"status":"ok","hotels":12,"regions":[...],"planner_configured":true}
```

`planner_configured` reports whether `ANTHROPIC_API_KEY` was found. The
tests need neither a key nor a network — only itinerary generation does.

### Frontend

In a second terminal, with the backend running:

```bash
cd frontend
npm install
npm run dev                               # http://localhost:5173
```

The dev server is pinned to port 5173 because the backend's CORS allowlist
names it. If the port is taken, Vite fails rather than moving to another one
where API calls would be silently blocked.

`VITE_API_BASE_URL` overrides the backend origin; it defaults to
`http://localhost:8000`.

## API

| Method | Path | |
|---|---|---|
| `GET` | `/api/health` | Catalogue size, supported regions, whether a key is configured |
| `POST` | `/api/itineraries` | A brief in, an itinerary out. Returns 200 with an unsupported-brief response when the catalogue cannot serve the destination — that is a product outcome, not an error |
| `POST` | `/api/itineraries/recompute` | Designer edits — change nights, replace a hotel. Deterministic; no model call |

Interactive docs at `http://localhost:8000/docs`.

## Environment variables

See [`.env.example`](.env.example). `.env` is gitignored and must never be
committed.

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | yes | Interpreting the brief and generating the itinerary |

| `VITE_API_BASE_URL` | no | Backend origin for the frontend. Defaults to `http://localhost:8000` |

## Repository layout

```text
backend/      FastAPI application and deterministic logic
frontend/     React + TypeScript application
data/         Supplied PIXI dataset + validate.py           (read-only)
docs/         APPROACH.md — product narrative
AGENTS.md     Working agreement for AI coding agents
CLAUDE.md     Imports AGENTS.md — Claude Code's entry point
BUILD_LOG.md  Build journal and time log
```
