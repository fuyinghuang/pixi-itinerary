# Build Log

Chronological journal of how the PIXI Itinerary Builder was built —
decisions, corrections, and time spent. Written as work happens rather
than reconstructed afterwards.

Time entries are marked _pending_ where elapsed time was not recorded.

---

## Session 1 — Problem exploration and planning

**Date:** 2026-09-06
**Time:** _pending_

### Inspected the supplied materials

Read the assignment brief, the repository README, `data/schema.md`,
`data/hotels.json`, `data/validate.py`, and `data/README.md` before
proposing anything.

Ran the supplied validator:

```bash
python3 data/validate.py
# OK: 12 hotels across 5 countries — all valid.
```

Notable observations from the dataset itself:

- 12 properties across five countries, but effectively **four coherent
  regions**: South Africa; East Africa (Kenya and Tanzania, which pair as
  one cross-border circuit); Japan; Italy.
- Image counts vary — 3, 4 and 5 all occur — so any layout assuming a
  fixed count would break.
- `access_notes` is present on every property and is specific, human
  written, and publishable as-is.
- The local interpreter is Python 3.9.6, and `validate.py` already relies
  on PEP 585 builtin generics, so 3.9 is a real floor rather than a
  defensive guess.

### Decisions

**FastAPI over Django.** The brief permits either. Pydantic gives
schema-validated model output and the API contract from a single
definition, which is exactly what the architecture needs. Django's ORM,
admin and auth would go unused.

**No vector search.** A 12-hotel catalogue fits in a prompt. Embeddings
and a vector store would be infrastructure performing sophistication
rather than delivering it. Recorded as a timebox decision, not a claim
that retrieval is wrong at PIXI's real scale.

**Semantic planning separated from deterministic facts.** The model owns
interpretation, selection, sequencing, night allocation and language, and
may emit planning values such as nights per stop. Derived prices,
distances, durations and totals come from deterministic Python or supplied
dataset fields. Enforced structurally: the response schema carries no
price, distance or duration fields.

**One initial LLM planning call.** It may return both the interpreted
brief and the proposed plan. Splitting into separate parse and plan calls
was considered and deferred — it doubles latency for a benefit we have not
yet demonstrated we need.

**Duration and Day N, not calendar dates.** The dataset supports no
seasonality, availability, or date-dependent pricing, so calendar logic
would imply precision the data cannot back.

### Corrections to the initial AI-generated plan

These are the points where the first proposal was changed on review.

**Persistence removed from the core MVP.** The initial plan included a
JSON-file store so share links would genuinely work. On review, the
assignment does not require persistence, and it drags in identifiers,
serialisation and file lifecycle for a requirement we added ourselves. The
client view became an in-app read-only preview. A persistent share link is
a stretch goal if time remains.

**Editing reduced from three controls to two.** The initial plan proposed
change nights, replace hotel, and change room category. Room category adds
little signal for the core product thesis — that AI proposes and the
designer retains control — so the MVP keeps **change nights** and
**replace hotel** only. Consequence: `rooms[].rate_delta` goes unused, and
that is stated explicitly rather than left to look like an oversight.

**Testing scope loosened.** The initial plan said "unit tests on the
deterministic engine only, nothing else", which was too absolute. Final
position: unit-test the deterministic domain logic, manually verify the
complete end-to-end journey, add a cheap API happy-path test if
inexpensive, and treat frontend automated tests as optional.

**Contract wording corrected.** The initial plan described "one shared
`Itinerary` type across backend and frontend". There is no shared type —
there are two representations kept in sync by hand. Restated: the backend
Pydantic schemas are the canonical API contract, mirrored manually in
TypeScript for the MVP.

### The transfer-routing correction

The most consequential change, and a real example of AI accelerating
exploration while human review changed the engineering outcome.

**What AI proposed.** The initial architecture included a transfer engine:
haversine distance between consecutive stops, transport-mode inference
from distance and airport codes, duration estimates, and a mock transfer
rate card feeding into the total price. It was plausible, self-consistent,
and would have taken two to three hours to build.

**The challenge.** Does this actually improve the product, or is it
engineering for its own sake? The brief asks for an itinerary product, not
a route planner, and explicitly permits mocked or estimated data where a
real integration would otherwise be needed.

**What re-inspection of the data showed.** Reading every `access_notes`
value made the answer clear — inferred routing would have *contradicted*
the supplied information on real legs in this catalogue:

- *Giraffe Manor → Angama Mara.* Both list `NBO` as nearest airport. A
  "same airport means road transfer" rule is flatly wrong; the supplied
  notes describe a scheduled light aircraft from Nairobi Wilson.
- *andBeyond Ngorongoro → Singita Grumeti.* Both list `JRO`, roughly
  110 km apart in a straight line. A distance threshold generous enough to
  fix the Nairobi case classifies this as a drive. The supplied notes say
  *"Bush flight… Not road-accessible for guests."*

Patching these would mean encoding enough exceptions that the computation
is decoration over a lookup table — while producing numbers less accurate
than the strings already in the dataset.

**Decision.** The synthetic routing engine was removed. Haversine,
mode inference, duration estimation and transfer pricing are all out.
Transfer information stays grounded in `nearest_airport`, `access_notes`,
and origin/destination hotel facts. Narrative may reference that a
transfer exists, but specifics come from the supplied field rather than
generated prose.

**Why this is the right call.** *"We surface the supplied routing rather
than simulating a logistics engine; in production this is a routing or
travel-logistics integration"* is a stronger position than defending
invented precision — particularly to an audience who knows this domain far
better than we do. It also freed roughly two to three hours for hardening
and visual quality, which is where a DAM company will actually look.

### `AGENTS.md` review

Reviewed the working agreement before implementation and restructured it.
The substantive changes:

- Split "Product and Architecture Invariants" into **Invariants** (true
  regardless of scope) and **Current MVP Scope** (time-boxed and
  revisable). Previously, "no persistence" carried the same weight as "no
  hallucinated hotels", which is how a timebox decision quietly becomes a
  claimed architectural position.
- Promoted "never commit secrets" from a buried bullet back to a numbered
  rule — it is an explicit assignment deliverable.
- Added three missing operational invariants: `data/` is read-only, nights
  arithmetic (every stop ≥ 1 night, nights sum to the requested duration),
  and the failure path (one repair attempt, then a graceful recoverable
  error state, never a 500 or a blank screen).
- Made the pricing formula explicit so an agent cannot silently decide
  whether to apply `rate_delta`.
- Named the four supported regions and specified an honest
  unsupported-state response, which had been missing entirely despite
  being the first thing unscripted input will hit.
- Removed a Boundaries section in which nine of twelve bullets restated
  rules stated elsewhere — duplicated rules drift.

Two of the review's own recommendations were rejected on further review:

- *"The LLM must not emit these values at all"* was too broad, since the
  model legitimately emits `nights_per_stop`. Narrowed to derived prices,
  distances, transfer durations and calculated totals.
- *"`access_notes` verbatim, never paraphrased"* was too rigid for
  producing readable client-facing copy. Relaxed: `access_notes` is the
  source of truth, and narrative must not introduce specifics the field
  does not contain.
- *"one repair attempt, then a deterministic fallback"* promised a
  fallback that has not been designed yet. Softened to a graceful,
  recoverable error state, to be upgraded once a real fallback exists.
  Documentation should not commit to behaviour ahead of the design.

### Documentation aligned

Updated `README.md` to match the locked decisions and the actual state of
the repository: removed the shareable-link wording in favour of an in-app
client preview, corrected the over-broad claim that the model never emits
any number, removed setup commands for a backend and frontend that do not
exist, and reduced the environment table to the one variable actually
established. `python3 data/validate.py` remains documented because it
genuinely works.

Created `docs/APPROACH.md` as a working skeleton and this build log.

### Incidents

`AGENTS.md` was accidentally overwritten with prompt text during the
session. There were no commits, so nothing to restore from — the content
was recovered from the session context. This is the reason the
documentation scaffold is being committed before implementation begins.

---

## Session 2 — _pending_

**Time:** _pending_

---

## Time summary

_Pending._ Totals are compiled here and mirrored into
[`docs/APPROACH.md`](docs/APPROACH.md) §14.

| Session | Focus | Time |
|---|---|---|
| 1 | Problem exploration, planning, working agreement, documentation | pending |
