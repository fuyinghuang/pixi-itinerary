import { useRef, useState } from "react";

import { ApiError, generateItinerary, recomputeItinerary } from "./api";
import BriefForm from "./components/BriefForm";
import ItineraryView from "./components/ItineraryView";
import type {
  Itinerary,
  RecomputeRequest,
  RecomputeStop,
  UnsupportedBriefResponse,
} from "./types";
import { REGION_LABELS, isItinerary } from "./types";

/**
 * Every state the screen can be in. A discriminated union so the compiler
 * insists each one is handled — including the unsupported brief, which is a
 * normal outcome rather than an error.
 */
type View =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "itinerary"; data: Itinerary }
  | { kind: "unsupported"; data: UnsupportedBriefResponse }
  | { kind: "error"; message: string; retryable: boolean };

/** The stops as the designer owns them: what to send back on an edit. */
const toEditableStops = (itinerary: Itinerary): RecomputeStop[] =>
  itinerary.stops.map((stop) => ({
    hotel_id: stop.hotel.id,
    nights: stop.nights,
    rationale: stop.rationale,
  }));

export default function App() {
  const [brief, setBrief] = useState("");
  const [view, setView] = useState<View>({ kind: "idle" });
  const [busy, setBusy] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  /** The same itinerary, shown as the client would receive it. */
  const [preview, setPreview] = useState(false);
  const inFlight = useRef<AbortController | null>(null);

  async function build() {
    const trimmed = brief.trim();
    if (!trimmed) return;

    // A second submit supersedes the first rather than racing it.
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;

    setEditError(null);
    setPreview(false);
    setView({ kind: "loading" });

    try {
      const result = await generateItinerary(trimmed, controller.signal);
      if (controller.signal.aborted) return;
      setView(
        isItinerary(result)
          ? { kind: "itinerary", data: result }
          : { kind: "unsupported", data: result },
      );
    } catch (error) {
      if (controller.signal.aborted) return;
      setView(
        error instanceof ApiError
          ? { kind: "error", message: error.message, retryable: error.retryable }
          : {
              kind: "error",
              message: "Something went wrong building the itinerary.",
              retryable: true,
            },
      );
    } finally {
      if (inFlight.current === controller) inFlight.current = null;
    }
  }

  /**
   * Apply an edit by asking the backend to rebuild the itinerary. Nothing is
   * computed here — every price, day range and total comes back from the
   * catalogue, so an optimistic local guess would only be able to be wrong.
   */
  async function applyEdit(current: Itinerary, stops: RecomputeStop[]) {
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;

    setBusy(true);
    setEditError(null);

    const request: RecomputeRequest = {
      trip_region: current.trip_region,
      trip_length_unit: current.trip_length.unit,
      interpreted_brief: current.interpreted_brief,
      narrative: current.narrative,
      stops,
    };

    try {
      const updated = await recomputeItinerary(request, controller.signal);
      if (controller.signal.aborted) return;
      setView({ kind: "itinerary", data: updated });
    } catch (error) {
      if (controller.signal.aborted) return;
      // The itinerary on screen is left alone; only the message is new.
      setEditError(
        error instanceof ApiError
          ? error.message
          : "That change could not be applied.",
      );
    } finally {
      if (inFlight.current === controller) inFlight.current = null;
      setBusy(false);
    }
  }

  function changeNights(stopIndex: number, nights: number) {
    if (view.kind !== "itinerary") return;
    const stops = toEditableStops(view.data);
    stops[stopIndex] = { ...stops[stopIndex], nights };
    void applyEdit(view.data, stops);
  }

  function replaceHotel(stopIndex: number, hotelId: string) {
    if (view.kind !== "itinerary") return;
    const stops = toEditableStops(view.data);
    // The rationale explains why the model chose the property being replaced.
    // Carrying it over would attach it to a hotel the model never picked, so
    // it is cleared rather than presented as current.
    stops[stopIndex] = { ...stops[stopIndex], hotel_id: hotelId, rationale: "" };
    void applyEdit(view.data, stops);
  }

  const hasItinerary = view.kind === "itinerary";

  return (
    <div className={preview ? "page preview" : "page"}>
      {!preview && (
        <header className="masthead">
          <h1>PIXI Itinerary Builder</h1>
          <p>From a client's own words to a sequenced, image-led proposal.</p>
        </header>
      )}

      {!preview && (
        <BriefForm
          value={brief}
          onChange={setBrief}
          onSubmit={build}
          disabled={view.kind === "loading" || busy}
        />
      )}

      {hasItinerary && (
        <div className="view-switch">
          <button
            type="button"
            className="link"
            onClick={() => setPreview((on) => !on)}
          >
            {preview ? "Back to editing" : "Preview as client"}
          </button>
        </div>
      )}

      <div aria-live="polite">
        {view.kind === "loading" && (
          <section className="status">
            <h2>Building your itinerary…</h2>
            <p>This may take around 15–20 seconds.</p>
          </section>
        )}

        {view.kind === "unsupported" && (
          <section className="status">
            <h2>PIXI's catalogue can't cover that trip</h2>
            <p>{view.data.reason}</p>
            <ul className="region-list">
              {view.data.supported_regions.map((region) => (
                <li key={region}>{REGION_LABELS[region] ?? region}</li>
              ))}
            </ul>
            <p>Edit the brief above to try one of these instead.</p>
          </section>
        )}

        {view.kind === "error" && (
          <section className="status error">
            <h2>That didn't work</h2>
            <p>{view.message}</p>
            {view.retryable && (
              <button type="button" onClick={build}>
                Try again
              </button>
            )}
          </section>
        )}
      </div>

      {view.kind === "itinerary" && (
        <ItineraryView
          itinerary={view.data}
          busy={busy}
          editError={editError}
          preview={preview}
          onNightsChange={changeNights}
          onReplace={replaceHotel}
        />
      )}
    </div>
  );
}
