import type { ItineraryStop } from "../types";

const money = (amount: number, currency: string) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);

const dayRange = (from: number, to: number) =>
  from === to ? `Day ${from}` : `Day ${from}–${to}`;

const nightCount = (nights: number) =>
  `${nights} ${nights === 1 ? "night" : "nights"}`;

interface Props {
  stop: ItineraryStop;
  currency: string;
  /** Edits are disabled while a recompute is in flight. */
  busy: boolean;
  onNightsChange: (nights: number) => void;
  onReplace: (hotelId: string) => void;
}

export default function StopCard({
  stop,
  currency,
  busy,
  onNightsChange,
  onReplace,
}: Props) {
  const { hotel } = stop;
  const alternatives = stop.replacement_options;

  return (
    <li className="stop">
      {/* Counts vary between three and five; the layout adapts rather than
          assuming a number. */}
      <div className="gallery">
        {hotel.images.map((src, index) => (
          <img
            key={src}
            src={src}
            alt={
              index === 0
                ? hotel.name
                : `${hotel.name}, photograph ${index + 1}`
            }
            loading="lazy"
            decoding="async"
          />
        ))}
      </div>

      <div className="stop-body">
        <p className="stop-days">
          {dayRange(stop.day_from, stop.day_to)} · {nightCount(stop.nights)}
        </p>
        <h3>{hotel.name}</h3>
        <p className="stop-place">
          {hotel.city}, {hotel.region}
          {hotel.brand ? ` · ${hotel.brand}` : ""}
        </p>

        <div className="edits">
          <div className="edit">
            <span className="edit-label">Nights</span>
            <div className="stepper">
              <button
                type="button"
                onClick={() => onNightsChange(stop.nights - 1)}
                disabled={busy || stop.nights <= 1}
                aria-label={`One fewer night at ${hotel.name}`}
              >
                −
              </button>
              <output>{stop.nights}</output>
              <button
                type="button"
                onClick={() => onNightsChange(stop.nights + 1)}
                disabled={busy}
                aria-label={`One more night at ${hotel.name}`}
              >
                +
              </button>
            </div>
          </div>

          <div className="edit">
            <span className="edit-label">Replace</span>
            {alternatives.length > 0 ? (
              <select
                value=""
                disabled={busy}
                aria-label={`Replace ${hotel.name}`}
                onChange={(event) => {
                  if (event.target.value) onReplace(event.target.value);
                }}
              >
                <option value="">Choose a property…</option>
                {alternatives.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name} — {option.city}
                  </option>
                ))}
              </select>
            ) : (
              <p className="no-alternatives">
                You're already using all available PIXI properties in this
                region.
              </p>
            )}
          </div>
        </div>

        {/* Empty after a designer swap: the model never chose this property,
            so there is no rationale to show. */}
        {stop.rationale && <p className="rationale">{stop.rationale}</p>}

        {hotel.tags.length > 0 && (
          <ul className="tags">
            {hotel.tags.map((tag) => (
              <li key={tag}>{tag}</li>
            ))}
          </ul>
        )}

        {/* Supplied verbatim. Nothing here is inferred or rewritten. */}
        {hotel.access_notes && (
          <p className="access">
            <span>Getting there · {hotel.nearest_airport.iata}</span>
            {hotel.access_notes}
          </p>
        )}

        <p className="stop-cost">
          <span>
            {nightCount(stop.nights)} ×{" "}
            {money(hotel.approx_nightly_rate, currency)}
          </span>
          <strong>{money(stop.subtotal, currency)}</strong>
        </p>
      </div>
    </li>
  );
}
