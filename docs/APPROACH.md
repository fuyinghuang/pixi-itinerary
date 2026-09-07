# Approach

Product narrative for the PIXI AI Product Engineer take-home exercise.

> **Status: working skeleton.** Sections marked _pending_ are filled in as
> the build progresses. This document records decisions as they are made,
> not reconstructed afterwards.

## 1. Interpretation of the problem

PIXI is a DAM platform: hotels pay to host photography and content, and
travel designers source that content for client proposals. The brief's
stated outcome is that designers *engage more deeply with PIXI by using
PIXI content to create a client itinerary*, ending with something a client
can view, respond to, and ultimately book against.

Today that work is manual — Canva, PDF templates, dated portals. The
designer researches properties, sequences them, works out how the client
physically moves between them, estimates cost, and assembles it into
something worth sending. Output quality tracks how much time the designer
had.

The brief deliberately does not define the product or the interaction
model. Choosing what to build is part of the exercise.

## 2. Target user and outcome

**Primary user:** the travel designer, working against a client brief
written in the client's own words.

**Outcome:** the designer goes from a paragraph of client intent to a
sequenced, image-led itinerary they would be willing to put in front of a
client — in minutes, with their judgement still in control of the result.

**Secondary audience:** the client, who sees the finished artefact.

## 3. Concepts considered

| Concept | Why not (for the MVP) |
|---|---|
| Voice-led itinerary creation | Demo-fragile, and the interesting problem is grounding, not transcription |
| Conversational multi-turn chat | Turns the product into a chat wrapper; the designer's real need is an artefact, not a dialogue |
| Client preference capture and reuse | Valuable, but only after there is an itinerary worth personalising |
| Intelligent hotel discovery and matching | With 12 properties across four regions, retrieval is close to trivial — this would perform sophistication rather than deliver it |
| Client-facing interactive itinerary | Retained, in reduced form, as the preview stage |
| **Brief → itinerary → designer edits → client preview** | **Selected** |

## 4. Selected MVP

```text
client brief
  → LLM proposes a grounded itinerary
  → deterministic validation and pricing
  → designer reviews
  → change nights / replace hotel
  → client-facing preview
```

Five stages, one coherent journey, ending in an artefact that is
recognisably useful.

## 5. Why this is the smallest strong slice

- It is the journey the brief's own worked example implies.
- It satisfies every "must include" item — working frontend and backend, a
  live LLM doing meaningful work, real use of the supplied content and
  imagery, one coherent journey, a useful output — without padding.
- The split between model judgement and deterministic computation will be
  visible in the architecture rather than merely claimed.
- The edit stage is what distinguishes a tool from a demo: it shows the
  designer retains control, and it costs little because it reuses the
  deterministic layer the itinerary already depends on.
- The client preview is the artefact PIXI actually cares about — hotel
  imagery presented as a proposal, not as metadata.

## 6. Deliberately outside the timebox

Not rejected as architecture — excluded from a 12–16 hour build. Each is a
natural next step.

- Persistence and shareable URLs
- Room-category selection and free-form day editing
- Calendar dates, seasonality, availability, date-dependent pricing
- Routing or transfer computation (see §7)
- Vector search or embeddings over a 12-hotel catalogue
- Authentication, databases, Docker, CI, PDF export
- Flights, experiences, and booking

## 7. The AI / deterministic responsibility boundary

This is the central architectural decision.

**The model owns judgement and language.** Interpreting the brief,
selecting properties, sequencing stops, allocating nights, and writing
rationale and narrative copy. It may emit planning values it is
responsible for, such as nights per stop.

**Deterministic code and supplied data own facts.** Prices, totals, hotel
attributes, airports, and access information. The model does not author
derived prices, distances, transfer durations, or calculated totals.

The boundary will be enforced structurally rather than by prompt
discipline: the model's response schema will carry no price, distance, or
duration fields, so a violation becomes a schema error rather than
something to catch in review.

### Transfers: a correction worth recording

The first design included a routing engine — haversine distances,
transport-mode inference, duration estimates, and a mock transfer rate
card. Re-reading the supplied `access_notes` showed this was both
unnecessary and actively risky: inferred routing would have contradicted
the supplied data on real legs in this catalogue. The routing engine was
removed. Transfer information stays grounded in `nearest_airport`,
`access_notes`, and hotel facts. Full reasoning in
[`BUILD_LOG.md`](../BUILD_LOG.md).

In production this is a routing or travel-logistics integration, not
something to simulate.

## 8. Assignment requirements vs our decisions

Keeping these separate matters — we should be able to say which is which.

**Required by the brief**

- Python backend; React + TypeScript frontend
- A working frontend and backend
- A live LLM used for a meaningful part of the experience
- Meaningful use of the supplied hotel content and imagery
- One coherent end-to-end journey
- An output recognisably useful to the designer or their client
- Setup instructions that work; `.env.example`; no committed credentials
- 12–16 hours within four calendar days

**Our product and engineering decisions**

- FastAPI over Django — Pydantic gives schema-validated model output and
  the API contract from one definition; Django's ORM, admin and auth are
  unused weight here
- The model never authors derived facts, enforced by schema
- Transfer information grounded in supplied data rather than computed
- No persistence in the core MVP; the client view is an in-app preview
- Editing limited to two controls: change nights, replace hotel
- Trip length as a duration with Day N structure, not calendar dates
- No vector search over a 12-hotel catalogue
- Backend Pydantic schemas as the canonical contract, mirrored by hand in
  TypeScript
- `data/` treated as read-only, though the dataset README permits
  extension

## 9. Assumptions

- Trip length arrives as a duration ("10 days"), not as calendar dates. It
  is stated in days or nights and normalised deterministically: N days →
  N − 1 accommodation nights; N nights → N nights. Days and nights are
  never equated.
- Pricing is accommodation only: `nights × approx_nightly_rate`, base room
  category, one room, USD. Indicative, not quoted.
- `rooms[].rate_delta` is deliberately unused. Room-category selection is
  outside the MVP (§6), so every stop is priced at the base category. This
  is a scope decision, not an oversight, and is stated in the UI.
- Flights, transfers, experiences, taxes and fees are excluded and said to
  be excluded.
- The catalogue supports four coherent regions — South Africa; East Africa
  (Kenya and Tanzania as one circuit); Japan; Italy — and a trip stays
  within one.
- Party size shapes narrative and property fit, not price.
- Placeholder imagery stands in for PIXI DAM assets.

## 10. Risks

- **Unscripted input.** Evaluators will type their own briefs, including
  destinations the catalogue cannot serve. An honest unsupported-state
  response is a product requirement, not an edge case.
- **Model latency during a live demo.** Mitigated by echoing the
  interpreted brief early and keeping edits free of model calls.
- **Invalid model output** — unknown hotel IDs, nights that do not sum.
  Validation, one repair attempt, then a graceful recoverable error state.
- **Facts leaking into generated prose**, particularly transfer specifics.
  Mitigated by the schema constraint and by sourcing transfer detail from
  `access_notes`.
- **A thin catalogue making the AI look trivial.** Addressed by putting
  the model where it genuinely works — interpretation, sequencing, pacing,
  and language.
- **Output that impresses engineers but not designers.** The test is
  whether it looks sendable to a client.

## 11. Testing and verification

_Working section — expanded as the implementation lands._

Testing effort goes where incorrect behaviour would quietly weaken the
product or the architecture story, rather than spread evenly.

- **Deterministic domain logic — unit tested.** Validation, nights
  arithmetic, pricing, and the assembly of transfer information from
  supplied fields. These are pure functions over the dataset, cheap to
  test, and the place where a bug is silent rather than obvious.
- **A lightweight API happy-path or contract test**, if it is inexpensive.
  Enough to catch a broken response shape between backend and frontend.
- **Manual end-to-end verification** of the complete journey — brief,
  generated itinerary, validation and pricing, designer edits, client
  preview — including unscripted and unsupported briefs. Recorded in
  [`BUILD_LOG.md`](../BUILD_LOG.md) rather than asserted here.
- **Frontend automated tests** only if time remains.

Not covered by tests within the timebox: model output quality. A single
planning call is inspected by hand rather than evaluated systematically.

**At production scale** this is the part that changes most. Model output
quality needs an evaluation harness with a fixed brief set and regression
checks on grounding — hallucinated IDs, incoherent regions, nights that do
not sum — plus observability on latency, repair rate, and unsupported-brief
frequency. Those signals, not unit tests, are what would tell PIXI whether
the feature is working for designers.

## 12. Productionisation and next steps

_Pending — outline only._

- Persistence and shareable client links
- Real transfer and flight data via a routing or travel-logistics provider
- Live rates, availability, and seasonality
- The full PIXI DAM as the image source, replacing placeholders
- A catalogue large enough to make retrieval a real problem, and the
  retrieval strategy that follows
- Designer accounts, saved briefs, client preference reuse
- Observability on model output quality; evaluation harness for
  regressions
- Deployment, CI, authentication

## 13. AI-enabled development process

_Pending — populated from [`BUILD_LOG.md`](../BUILD_LOG.md)._

To cover: which tools were used and for what; how AI accelerated
exploration, design and implementation; where AI output was rejected,
corrected or improved; how the concept changed through iteration; where
human judgement mattered most.

The clearest example so far is the removal of the proposed routing engine
(§7). Others recorded in the build log as they occur.

## 14. Time spent

_Pending._ Recorded per session in [`BUILD_LOG.md`](../BUILD_LOG.md) and
summarised here at the end.

| Area | Time |
|---|---|
| Problem exploration and planning | pending |
| Backend and domain logic | pending |
| LLM integration | pending |
| Frontend | pending |
| Hardening and verification | pending |
| Documentation | pending |

## 15. What I learned

_Pending._
