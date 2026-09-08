import type { Itinerary } from "../types";
import { REGION_LABELS } from "../types";
import PriceSummary from "./PriceSummary";
import StopCard from "./StopCard";

interface Props {
  itinerary: Itinerary;
  busy: boolean;
  editError: string | null;
  /** The client-facing view: current state only, no tools, no history. */
  preview: boolean;
  onNightsChange: (stopIndex: number, nights: number) => void;
  onReplace: (stopIndex: number, hotelId: string) => void;
}

const plural = (count: number, word: string) =>
  `${count} ${count === 1 ? word : `${word}s`}`;

export default function ItineraryView({
  itinerary,
  busy,
  editError,
  preview,
  onNightsChange,
  onReplace,
}: Props) {
  const { trip_length: length } = itinerary;
  const region = REGION_LABELS[itinerary.trip_region] ?? itinerary.trip_region;
  const duration = plural(length.value, length.unit.slice(0, -1));

  return (
    <article className={busy ? "itinerary busy" : "itinerary"}>
      <header className="itinerary-header">
        {/* Derived from the current itinerary, so it stays correct after an
            edit. The model's own copy sits below as historical context. */}
        <h2>
          {region} · {duration} · {plural(itinerary.stops.length, "stop")}
        </h2>

        {/* The model's own copy describes the proposal it made, not the
            itinerary after an edit. It stays available to the designer as
            history, and is kept out of the client's view entirely. */}
        {!preview && (
          <section className="proposal" aria-label="Original AI proposal">
            <h3>Original brief interpretation</h3>
            <p>{itinerary.interpreted_brief}</p>

            <h3>Original proposal narrative</h3>
            <p className="narrative">{itinerary.narrative}</p>
          </section>
        )}
      </header>

      {!preview && (
        <div aria-live="polite">
          {busy && <p className="edit-status">Updating the itinerary…</p>}
          {editError && !busy && (
            <p className="edit-status error">{editError}</p>
          )}
        </div>
      )}

      <ol className="stops">
        {itinerary.stops.map((stop, index) => (
          <StopCard
            key={`${stop.hotel.id}-${stop.day_from}`}
            stop={stop}
            currency={itinerary.currency}
            busy={busy}
            preview={preview}
            onNightsChange={(nights) => onNightsChange(index, nights)}
            onReplace={(hotelId) => onReplace(index, hotelId)}
          />
        ))}
      </ol>

      <PriceSummary itinerary={itinerary} />
    </article>
  );
}
