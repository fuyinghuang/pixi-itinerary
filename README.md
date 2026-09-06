# PIXI Itinerary Builder

Turns a travel designer's client brief into a sequenced, imagery-rich
luxury itinerary drawn from PIXI's supplied hotel catalogue.

Built for the PIXI AI Product Engineer take-home exercise. The product
reasoning — what was considered, what was chosen, and why — is in
[`docs/APPROACH.md`](docs/APPROACH.md). A running build journal is in
[`BUILD_LOG.md`](BUILD_LOG.md).

> **Status: documentation scaffold.** The backend and frontend have not
> been built yet. The only thing that runs today is dataset validation.
> Setup instructions for the application are added here once those
> projects exist and have been verified — not before.

## What it will do

_Planned product behaviour. None of this runs yet — see Status above._

A designer pastes the client's own words — *"10 days in South Africa for
our anniversary, a few days in Cape Town, some time in the winelands, then
safari to finish"* — and gets back a day-by-day itinerary they can adjust
and then present to the client.

The journey:

```text
client brief
  → the model proposes a grounded itinerary
  → deterministic validation and pricing
  → the designer reviews
  → change nights / replace a hotel
  → client-facing preview
```

The model will handle judgement and language: interpreting the brief,
choosing properties, sequencing stops, allocating nights, and writing the
rationale and narrative. It may propose planning values such as nights per
stop.

It will not author derived prices, distances, transfer durations, or
calculated totals. Those come from deterministic Python or directly from
supplied dataset fields, and every hotel referenced is validated against
the supplied catalogue.

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
- An Anthropic API key (required once the LLM integration exists)

Frontend prerequisites are documented once the frontend is scaffolded and
its toolchain requirements are verified.

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

This is the only command that works today.

## Environment variables

See [`.env.example`](.env.example). `.env` is gitignored and must never be
committed.

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | yes | Interpreting the brief and generating the itinerary |

Further variables are documented here as the backend and frontend are
built and their configuration is actually established.

## Repository layout

```text
backend/      FastAPI application and deterministic logic   (not yet)
frontend/     React + TypeScript application                (not yet)
data/         Supplied PIXI dataset + validate.py           (read-only)
docs/         APPROACH.md — product narrative
AGENTS.md     Working agreement for AI coding agents
CLAUDE.md     Imports AGENTS.md — Claude Code's entry point
BUILD_LOG.md  Build journal and time log
```
