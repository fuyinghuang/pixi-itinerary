import type { Itinerary } from "../types";

export default function PriceSummary({ itinerary }: { itinerary: Itinerary }) {
  const total = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: itinerary.currency,
    maximumFractionDigits: 0,
  }).format(itinerary.accommodation_total);

  return (
    <section className="summary" aria-label="Price summary">
      <dl className="summary-total">
        <dt>
          Accommodation, {itinerary.accommodation_nights}{" "}
          {itinerary.accommodation_nights === 1 ? "night" : "nights"}
        </dt>
        <dd>{total}</dd>
      </dl>
      {/* Supplied by the backend so the wording stays with the pricing rule. */}
      <p className="price-note">{itinerary.price_note}</p>
    </section>
  );
}
