import type { Baseline } from "../baseline";
import { stopCopy } from "../baseline";
import type { Itinerary, TripLength } from "../types";
import { REGION_LABELS } from "../types";
import PriceSummary from "./PriceSummary";
import StopCard from "./StopCard";

interface Props {
  itinerary: Itinerary;
  /** What this itinerary was generated with, and what its copy was written for. */
  baseline: Baseline;
  busy: boolean;
  editError: string | null;
  /** The client-facing view: current state only, no tools, no history. */
  preview: boolean;
  onNightsChange: (stopIndex: number, nights: number) => void;
  onReplace: (stopIndex: number, hotelId: string) => void;
  /** Resolves to whether the save succeeded. */
  onRationaleSave: (stopIndex: number, rationale: string) => Promise<boolean>;
}

const plural = (count: number, word: string) =>
  `${count} ${count === 1 ? word : `${word}s`}`;

/** "10 days", "1 night" — in the unit the trip was stated in. */
const formatLength = (length: TripLength) =>
  plural(length.value, length.unit.slice(0, -1));

export default function ItineraryView({
  itinerary,
  baseline,
  busy,
  editError,
  preview,
  onNightsChange,
  onReplace,
  onRationaleSave,
}: Props) {
  const { trip_length: length } = itinerary;
  const originalLength = baseline.tripLength;
  const region = REGION_LABELS[itinerary.trip_region] ?? itinerary.trip_region;
  const duration = formatLength(length);
  // Both values come from the backend; nothing is recalculated here.
  const lengthChanged =
    length.value !== originalLength.value || length.unit !== originalLength.unit;

  return (
    <article className={busy ? "itinerary busy" : "itinerary"}>
      <header className="itinerary-header">
        {/* Derived from the current itinerary, so it stays correct after an
            edit. The model's own copy sits below as historical context. */}
        <h2>
          {region} · {duration} · {plural(itinerary.stops.length, "stop")}
        </h2>

        {/* Edits may lengthen or shorten the trip. Compared with the length
            the itinerary was generated with — not necessarily what the client
            asked for — and shown to the designer only. */}
        {!preview && lengthChanged && (
          <p className="length-notice" role="status">
            Now {duration}. Original plan: {formatLength(originalLength)}.
          </p>
        )}

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
            // A hotel appears at most once, so its id is a stable key. Day
            // ranges are left out on purpose: they shift when an earlier
            // stop's nights change, which would remount the card and lose
            // an unsaved rationale draft.
            key={stop.hotel.id}
            stop={stop}
            copy={stopCopy(stop, baseline, preview ? "client" : "designer")}
            currency={itinerary.currency}
            busy={busy}
            preview={preview}
            onNightsChange={(nights) => onNightsChange(index, nights)}
            onReplace={(hotelId) => onReplace(index, hotelId)}
            onRationaleSave={(rationale) => onRationaleSave(index, rationale)}
          />
        ))}
      </ol>

      <PriceSummary itinerary={itinerary} />
    </article>
  );
}
