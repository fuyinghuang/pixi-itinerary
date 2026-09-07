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

export default function StopCard({
  stop,
  currency,
}: {
  stop: ItineraryStop;
  currency: string;
}) {
  const { hotel } = stop;

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

        <p className="rationale">{stop.rationale}</p>

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
