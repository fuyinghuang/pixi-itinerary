# Approach

Product narrative for the PIXI AI Product Engineer take-home exercise.

> Written as the build progressed rather than reconstructed afterwards.
> Time figures are provisional until final hardening and documentation are
> complete.

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
- The split between model judgement and deterministic computation is
  visible in the architecture rather than merely claimed.
- The edit stage is what distinguishes a tool from a demo: it shows the
  designer retains control, and it costs little because it reuses the
  deterministic layer the itinerary already depends on.
- The client preview is the artefact most directly aligned with the brief's
  stated outcome — hotel imagery presented as a proposal, not just as
  metadata.

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

The boundary is enforced structurally rather than by prompt discipline:
the model's response schema carries no price, distance, or travel-duration
field, so a violation is a schema error rather than something to catch in
review.

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
- **Model latency during a live demo.** Mitigated with an explicit loading
  state and by keeping subsequent edits free of model calls.
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

Testing effort goes where incorrect behaviour would quietly weaken the
product or the architecture story, rather than spread evenly.

- **Deterministic domain logic — unit tested.** Validation, nights
  arithmetic, pricing, and the assembly of transfer information from
  supplied fields. These are pure functions over the dataset, cheap to
  test, and the place where a bug is silent rather than obvious.
- **API contract tests** over the routes, covering the recompute path end
  to end and the error codes. Ten in total, none needing a key or a network.
- **Manual end-to-end verification** of the complete journey — brief,
  generated itinerary, validation and pricing, designer edits, client
  preview. Recorded in
  [`BUILD_LOG.md`](../BUILD_LOG.md) rather than asserted here.
- **Frontend automated tests** were not written. The journey was verified
  in a browser against the live backend instead, which is what caught the
  defects that mattered.

Not covered by tests within the timebox: model output quality. A single
planning call is inspected by hand rather than evaluated systematically.

**At production scale** this is the part that changes most. Model output
quality needs an evaluation harness with a fixed brief set and regression
checks on grounding — hallucinated IDs, incoherent regions, nights that do
not sum — plus observability on latency, repair rate, and unsupported-brief
frequency. Those signals, not unit tests, are what would tell PIXI whether
the feature is working for designers.

## 12. Productionisation and next steps

Two things would break first, and both are about knowing whether the
feature is working rather than whether it runs.

**What breaks first**

1. **No way to tell whether the model is doing well.** Every judgement about
   output quality in this build was made by reading one response at a time.
   That does not survive contact with real traffic. The first thing to build
   is an evaluation harness: a fixed set of briefs, scored on grounding —
   hotel ids that exist, one region per trip, nights that sum — plus the
   operational signals that reveal drift, chiefly repair rate and
   unsupported-brief frequency. Without it there is no way to know that a
   prompt change or a model upgrade made things worse.
2. **Latency.** A generation measured **16.96 seconds** end to end. It was
   left unoptimised deliberately, to keep the baseline honest, but a designer
   producing several proposals a day will feel it. The catalogue is a stable
   prompt prefix, so prompt caching is the first lever; lowering effort is the
   second; and past a few seconds the right answer is to stop holding the HTTP
   connection at all and stream progress instead.

**Then, as the product grows**

3. **Persistence and a real client link.** Today the client view is a mode,
   not a URL. The brief's outcome — something a client can *view, respond to
   and book against* — needs the itinerary to outlive the session, which
   means storage, identifiers and eventually accounts.
4. **Real transfer and rate data.** `access_notes` is authoritative for this
   catalogue but it is prose written for a fixture. Production wants a routing
   or travel-logistics provider for transfers, and live rates with seasonality
   and availability rather than a single indicative nightly figure.
5. **The DAM as the image source.** The placeholders stand in for the assets
   PIXI already owns. Replacing them is mostly plumbing, but it is the thing
   that makes the artefact feel like PIXI's rather than a demo's.
6. **Retrieval, once the catalogue justifies it.** With twelve properties the
   whole dataset fits in the prompt and selection is nearly forced. As the
   catalogue grows, sending all of it becomes increasingly inefficient and
   retrieval becomes a separate problem: filtering before the model sees
   anything, and evaluating whether the shortlist was right independently of
   whether the itinerary reads well.
7. **Deployment, authentication and CI.** Necessary for operating the product
   safely, but not the first uncertainties I would resolve.

**Product steps, distinct from hardening.** Above is what production demands.
What the *product* wants next is different: client preference capture and
reuse, so a returning couple does not start from a blank brief; a second
model pass that rewrites the narrative on request after edits; and richer
editing — reordering stops, room categories, adding a property the model did
not pick.

## 13. AI-enabled development process

**Tools, and what each was for.** Claude Code was used throughout: to
interrogate the brief and the dataset before any code, to argue through
architecture, to write the implementation, and to drive a browser for live
verification. Claude Opus 5 is also a component of the product itself, doing
the planning inside `planner.py`. A third use mattered more than expected: a
written working agreement in `AGENTS.md` that the agent had to follow, which
turned "don't invent facts" from a hope into a rule with a schema behind it.

The honest summary of how AI influenced the work is not that it made
everything faster. It produced plausible, internally consistent, *wrong*
architecture more than once, and the value came from checking its proposals
against the supplied data rather than from accepting them.

### Where AI output was rejected or corrected

**A routing engine that would have contradicted the data.** The first
architecture included haversine distances between stops, transport-mode
inference from airport codes, duration estimates and a mock transfer rate
card. It was coherent, and wrong. Reading every `access_notes` value showed
it would produce incorrect answers on real legs.
Giraffe Manor and Angama Mara share `NBO`, so a same-airport-means-drive
rule is flatly wrong where the supplied notes describe a scheduled light
aircraft. Distance fares no better: andBeyond Ngorongoro and Singita Grumeti
are 168km apart and connected by a bush flight the notes call *"not
road-accessible for guests"*, while Ngorongoro itself is reached from
Kilimanjaro by a four-to-five hour road transfer. Similar distances, opposite
answers — the mode lives in the supplied prose, not in the coordinates. The
engine was removed. Transfers now surface the supplied text instead —
smaller, more accurate, and easier to defend.

**A recommendation reversed by measurement.** Later, the same instinct for
safety produced the opposite error. To guarantee the model could never
paraphrase a transfer detail, the proposal was to withhold `access_notes`
from the prompt entirely. Checking the data first showed the cost was small
next to the signal, and that the claim hotel descriptions already carry
access character is false — `andbeyond-ngorongoro` and `singita-grumeti` are
both fly-in with no hint in their descriptions, while
`belmond-caruso-ravello` mentions a boat and is a road transfer. A middle
option, a hand-authored `access_character` label, collapsed on inspection
too: Ngorongoro's notes describe *both* a four-hour road transfer and a
flight, so any single label is a fact we would have invented. The
recommendation was withdrawn and the supplied text used as it stands.
The first live call confirmed the value — Londolozi was given four nights,
the longest stop, with the model's own reasoning that it is *"reached by
charter flight… so it earns a longer stay."*

**A defect only using the product could reveal.** Editing is deterministic by
design: no model call, so recompute is fast and the numbers are always the
backend's. But the model's prose rides along unchanged. Replacing Hotel de
Russie with Belmond Caruso left the Rome rationale — *"the single Rome
property in the catalogue"* — attached to a hotel in Ravello, and a nine-day
itinerary was titled *"an anniversary trip of 10 days"* directly beneath a
line reading 9 days. The fix was not to re-run the model, which would cost
~17 seconds per click, nor to discard all model-authored copy. Authority was
reordered instead: the heading is derived from current data, the original
proposal is retained as labelled historical context, and a replaced stop's
stale rationale is cleared rather than reattributed.

**A shorter one, caught before any code.** The contract originally carried
trip length as a single night count, quietly treating a ten-day brief as ten
nights. The dataset prices per night, so that is $1,800 wrong on a single
Londolozi stop. Trip length now carries a value *and* a unit, normalised
deterministically, and the rule survived a second attempt that reintroduced
the same conflation through the recompute path.

### How the concept changed

It got smaller three times and better each time. Persistence went first — the
assignment does not require it, and the client view works as a mode. Editing
dropped from three controls to two, because room categories add little to the
thesis that the designer stays in control. And the transfer engine went
entirely. What survived is a narrower product where every number is
defensible.

### Where judgment mattered most

Deciding what *not* to build, and checking claims against the data instead of
against plausibility. The routing engine, the `access_notes` reversal and the
days/nights bug were all caught the same way — by opening `hotels.json` and
counting, rather than by reading the proposal again. Plausibility is not
evidence; for this MVP, the supplied dataset is the source of truth.

## 14. Time spent

Recorded at the close of each session rather than reconstructed afterwards.
Provisional — final hardening and documentation time is not yet included.

| Session | Focus | Time |
|---|---|---|
| 1 | Problem exploration, planning, working agreement, documentation | ~2h |
| 2 | Verification pass, first commit, contract review | ~1.25h |
| 3 | Backend — catalogue, contract, itinerary logic, planner, API | ~6h |
| 4 | Frontend — read view, editing, client preview | ~3.25h |
| | **Total so far** | **~12.5h** |

The backend took roughly half the budget, and most of that went to contract
correctness rather than feature volume: the schemas, the validation rules and
the two corrections to how trip length is represented. The frontend was
comparatively quick because the deterministic layer meant it had no arithmetic
of its own to get wrong.

## 15. What I learned

**A tight constraint improved the product.** Twelve hotels across four regions
makes retrieval trivial, which initially looked like a limitation. It forced
the model's value into sequencing, pacing and language — which is where a
designer's judgement actually lives, and a better demonstration than search
would have been.

**Supplied data beat anything I could compute.** The instinct to build a
transfer engine was strong and wrong. `access_notes` is more accurate than
inference over coordinates, and the general lesson is to check whether the
answer is already in the data before deriving it.

**Determinism has an edge I did not anticipate.** Making edits instant by
never re-running the model is the right trade, but it means model-authored
prose can outlive the facts it describes. Structured data and generated copy
go stale at different rates, and a design that separates them has to decide
which one the interface treats as authoritative.

**I asserted an invariant and then broke it in CSS.** The rule that layout
must never assume a fixed image count is written in `AGENTS.md`, restated in a
TypeScript comment — and violated by a grid that only filled cleanly with five
images. Rules in prose do not enforce themselves; the ones that held were the
ones with a schema or a test behind them.

**Verification has to be adversarial to be worth anything.** Everything found
late was found by using the product rather than by rereading the code: the
gallery holes, the stale rationale, the contradictory heading. None was
caught by the automated tests I had at the time.
