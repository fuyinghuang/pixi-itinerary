import type { Itinerary } from "../types";
import { REGION_LABELS } from "../types";
import PriceSummary from "./PriceSummary";
import StopCard from "./StopCard";

export default function ItineraryView({ itinerary }: { itinerary: Itinerary }) {
  const { trip_length: length } = itinerary;

  return (
    <article className="itinerary">
      <header className="itinerary-header">
        <p className="interpreted">
          {REGION_LABELS[itinerary.trip_region] ?? itinerary.trip_region} ·{" "}
          {length.value} {length.value === 1 ? length.unit.slice(0, -1) : length.unit}
        </p>
        <h2>{itinerary.interpreted_brief}</h2>
        <p className="narrative">{itinerary.narrative}</p>
      </header>

      <ol className="stops">
        {itinerary.stops.map((stop) => (
          <StopCard
            key={`${stop.hotel.id}-${stop.day_from}`}
            stop={stop}
            currency={itinerary.currency}
          />
        ))}
      </ol>

      <PriceSummary itinerary={itinerary} />
    </article>
  );
}
