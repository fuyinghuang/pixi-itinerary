# AGENTS.md — Working Agreement for AI Coding Agents

PIXI Itinerary Builder turns a travel designer's client brief into a
sequenced, imagery-rich, send-ready luxury itinerary drawn from PIXI's
supplied hotel catalogue.

## Tech Stack

**Required by the brief**

- Backend: Python
- Frontend: React + TypeScript

**Our chosen implementation** (ours to defend, not mandated)

- FastAPI — Pydantic gives us schema-validated LLM output and the API
  contract from one model definition. The brief also permits Django.
- Vite for the frontend toolchain.
- Target Python 3.9. The local interpreter is 3.9.6 and the supplied
  `data/validate.py` already requires 3.9+. Use
  `from __future__ import annotations`. Do not use 3.10+ syntax such as
  `X | Y` in runtime-evaluated annotations, or `match`.

## Invariants

True regardless of scope. These do not change as the MVP grows.

### 1. The dataset is the source of truth

Hotel facts, imagery, airport information, access information, and pricing
inputs come from `data/hotels.json`. Never from generated text.

### 2. Derived facts are deterministic

The LLM may emit planning values it is responsible for, including
`stops[].nights`, stop ordering, and the trip length value and unit
extracted from the client's brief.

The LLM must not emit derived prices, distances, travel or transfer
durations, calculated totals, or other authoritative derived values. These
come from deterministic Python or from supplied dataset fields.

Enforce this structurally: the model's response schema must contain no
price, distance, or travel-duration field, so a violation is a schema error
rather than something to catch in review.

### 3. Hotel IDs are validated

Every `hotel_id` returned by the LLM is validated against
`data/hotels.json` before use. Never display or reference a hotel that is
not in the supplied catalogue.

### 4. Geographic support is explicit (`trip_region`)

The catalogue supports four coherent `trip_region` values — distinct from
the dataset's own `region` field, which is sub-national (`"Western Cape"`,
`"Kanto"`):

- South Africa
- East Africa (Kenya and Tanzania, which pair as one cross-border circuit)
- Japan
- Italy

An itinerary stays within one `trip_region`. Do not combine regions.
Replacing a hotel is constrained to the same `trip_region`.

An unsupported brief is a normal product outcome, not an API error. Return
HTTP 200 with the typed unsupported-brief response, including the supported
regions and useful alternatives. Never substitute a different destination
and present it as if it were requested. Never fail with an error or an
empty screen — evaluators will type unscripted input.

### 5. Transfer facts remain grounded

`access_notes` is the source of truth for how a guest reaches a property.

Do not build or infer a routing engine. Do not calculate transfer
distance, duration, transport mode, or transfer pricing.

Narrative copy may reference that a transfer exists and how it feels, but
specifics — durations, aircraft, transport modes, airport names — come
from the displayed `access_notes` string, not from generated prose.
Never introduce a transfer fact the field does not contain.

Use `nearest_airport`, `access_notes`, and origin/destination hotel facts.

### 6. The pricing formula is explicit

Accommodation price per stop is `nights × approx_nightly_rate`, at the base
room category, one room, in USD.

Because room-category selection is outside the MVP, `rooms[].rate_delta`
is deliberately unused. State this in the UI and in `docs/APPROACH.md` so
it reads as a decision rather than an oversight.

Label pricing as indicative, and state explicitly that flights, transfers,
and experiences are excluded. Do not introduce seasonality, availability,
taxes, or booking fees. Do not invent pricing assumptions silently.

### 7. Nights arithmetic

A brief states trip length in days or nights. Normalise it deterministically:

- N days → N − 1 accommodation nights
- N nights → N accommodation nights

Every stop has at least one night, and nights across stops sum to the
accommodation-night total — never to the day count. Preserve the stated
value and unit; days and nights are never equated.

On violation, repair or reject — never silently adjust the numbers to make
a plan fit.

### 8. Failure and repair behaviour

Invalid or unparseable model output gets one repair attempt. If it still
fails, return a graceful, recoverable error state rather than a 500 or a
blank screen. The demo is unscripted and must degrade gracefully.

A richer fallback may replace the error state once one has actually been
designed. Do not assume one exists.

### 9. The backend contract is canonical

Backend Pydantic schemas are the canonical API contract. The frontend
mirrors the shapes it consumes as hand-written TypeScript types.

When the contract changes, the schema and the types change in the same
commit. Do not introduce schema-generation or code-generation tooling
unless contract drift becomes a demonstrated problem.

### 10. Imagery is structural

Hotel imagery is part of the product experience, not decorative metadata.
PIXI's business is hotel photography.

The UI renders from each hotel's supplied `images` list, supports variable
image counts, hard-codes no image URL, and never assumes a fixed number of
images per hotel. The supplied placeholder URLs stand in for PIXI DAM
assets.

### 11. Never commit secrets

Real keys live in `.env`, which is gitignored. Commit `.env.example` only.
Never log, echo, or print an API key.

### 12. `data/` is read-only

Never modify `hotels.json`, `schema.md`, or `validate.py`.
`python3 data/validate.py` must keep passing.

`data/README.md` invites candidates to extend the dataset. We have
deliberately chosen not to: working within the supplied catalogue is the
constraint the exercise is about.

## Current MVP Scope

This section reflects the 12–16 hour timebox, not an architectural
position. Reasoning lives in `docs/APPROACH.md`.

**The core journey**

```text
client brief → generated itinerary → designer edits → client preview
```

**In scope**

- Trip length as a duration; itinerary rendered as Day 1, Day 2, Day 3
- Two designer edits: change nights, replace a hotel
- Edits re-run deterministic validation and pricing without another LLM call
- Client preview as an in-app read-only mode

**Deliberately outside this timebox** — not rejected as architecture

- Persistence, share-link storage, itinerary IDs that outlive the session
  (an in-memory id for rendering or recompute is fine)
- Calendar dates, seasonality, availability, date-dependent pricing
- Room-category editing, free-form day editing
- Routing or transfer computation
- Vector search or embeddings over a 12-hotel catalogue
- Authentication, databases, Docker, CI, PDF export

If one of these looks necessary, raise it as a scope change before
building it.

## Repository Structure

Target layout — some directories do not exist yet.

```text
backend/       FastAPI application and deterministic itinerary logic
frontend/      React + TypeScript application
data/          Supplied PIXI dataset, schema, and validation tools (read-only)
docs/          APPROACH.md — product narrative
README.md      Project overview and setup instructions
AGENTS.md      Working agreement for AI coding agents
CLAUDE.md      Claude Code entry point for these instructions
BUILD_LOG.md   Running development journal
```

Do not introduce additional layers or directories without a concrete need.

## Coding Principles

- Prefer the smallest solution that fully satisfies the requirement.
- Follow existing repository conventions before introducing new ones.
- Keep business rules separate from presentation code.
- Keep deterministic calculations separate from LLM-generated content.
- Preserve type safety across API boundaries.
- Handle loading, empty, unsupported, and error states explicitly.
- Prefer explicit, readable code over abstraction-heavy designs.
- Do not add a dependency unless it solves a demonstrated problem.
- Do not add infrastructure because it would be useful in production.

## Testing and Verification

Prioritise testing where incorrect behaviour would weaken the product or
the architecture story.

- Unit-test the deterministic domain logic.
- Validate dataset-driven behaviour.
- Manually verify the complete end-to-end journey.
- Add a lightweight API happy-path or contract test if it is inexpensive.
- Frontend automated tests are optional if time remains.

After a change, run the smallest relevant verification first — unit tests,
type checking, linting, dataset validation, or manual verification of the
affected journey.

Do not claim a change works unless it has been verified.

Before suggesting a commit: run the relevant checks, review the diff, check
for unrelated changes, check for secrets or environment files, check for
generated or temporary files, confirm the change forms one coherent unit,
and ask what input would break it.

Report what you found, including problems you did not fix and why.

## Working Agreement

Work as a senior engineering partner, not an autonomous code generator.

- Inspect the relevant code and documentation before proposing changes.
- State assumptions explicitly, and separate assignment requirements from
  engineering preferences.
- Explain important trade-offs and recommend an approach when there are
  several reasonable options.
- Do not modify unrelated code or refactor opportunistically.
- Stop before implementing anything that materially changes product scope
  or architecture, or adds a significant dependency. Explain the decision,
  the options, the trade-offs, and your recommendation.
- If you disagree with a proposed approach, say why rather than complying.
- Do not make a solution more sophisticated than the problem requires.

Optimise for correctness, clarity, product value, and the smallest
defensible implementation. Every important technical and product decision
should be explainable to a colleague who has not read this file.

## Decision Journal

`BUILD_LOG.md` records decisions, not terminal history. Update it without
being asked after a meaningful implementation slice or decision milestone:
what was built, the non-obvious trade-offs, what was verified, and any
disagreement that changed the product or the architecture.

Keep an implementation slice to roughly 5–10 lines:

```text
### Slice: <name>

Built         what changed, and the files it produced
Decision      2–4 sentences, only when the choice was not obvious
Verification  what ran, and the result
Correction    None, or the format below
```

Report a material disagreement before acting on it. Once resolved, log the
outcome under the current session as:

- **Original proposal or rule** · **Challenge** · **Evidence** ·
  **Final decision** · **Why**

Expand to 10–20 lines only for a disagreement that materially changed the
product or the architecture. Everything else stays short.

Do not log unresolved debate, trivial wording or naming differences, or which
command was retried. Never invent elapsed time — leave it `_pending_`. Do not
rewrite earlier entries to fit a newer format; correct facts, keep the record.

## Running the App

See [`README.md`](README.md). Do not document setup commands here, and do
not invent them before the corresponding tooling exists.

Dataset validation works today:

```bash
python3 data/validate.py
```
