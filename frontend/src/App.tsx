import { useRef, useState } from "react";

import { ApiError, generateItinerary } from "./api";
import BriefForm from "./components/BriefForm";
import ItineraryView from "./components/ItineraryView";
import type { Itinerary, UnsupportedBriefResponse } from "./types";
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

export default function App() {
  const [brief, setBrief] = useState("");
  const [view, setView] = useState<View>({ kind: "idle" });
  const inFlight = useRef<AbortController | null>(null);

  async function build() {
    const trimmed = brief.trim();
    if (!trimmed) return;

    // A second submit supersedes the first rather than racing it.
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;

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

  return (
    <div className="page">
      <header className="masthead">
        <h1>PIXI Itinerary Builder</h1>
        <p>From a client's own words to a sequenced, image-led proposal.</p>
      </header>

      <BriefForm
        value={brief}
        onChange={setBrief}
        onSubmit={build}
        disabled={view.kind === "loading"}
      />

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

      {view.kind === "itinerary" && <ItineraryView itinerary={view.data} />}
    </div>
  );
}
