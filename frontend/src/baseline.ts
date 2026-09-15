/**
 * What an itinerary's copy was written for, and what each stop card shows.
 *
 * Captured when an itinerary is generated. Changing nights or replacing a
 * hotel never changes it. The one update is a designer saving new rationale
 * text for a stop, which records that the text now fits that stop's current
 * nights. Staleness is always derived by comparing this record with the
 * current itinerary, never stored as a flag.
 */

import type { Itinerary, ItineraryStop, TripLength } from "./types";

/** Who wrote a stop's rationale, and for how many nights. */
export interface RationaleOrigin {
  nights: number;
  author: "model" | "designer";
}

export interface Baseline {
  /** The trip length the itinerary was generated with. Never updated. */
  tripLength: TripLength;
  /**
   * Keyed by hotel id rather than position, and held in App state rather
   * than a card, so it survives card remounts and edits to other stops.
   */
  rationaleByHotel: ReadonlyMap<string, RationaleOrigin>;
}

export function captureBaseline(itinerary: Itinerary): Baseline {
  return {
    tripLength: itinerary.trip_length,
    rationaleByHotel: new Map(
      itinerary.stops.map(
        (stop) =>
          [stop.hotel.id, { nights: stop.nights, author: "model" }] as const,
      ),
    ),
  };
}

/** The designer saved rationale text written for this stop's nights. */
export function recordDesignerRationale(
  baseline: Baseline,
  hotelId: string,
  nights: number,
): Baseline {
  const rationaleByHotel = new Map(baseline.rationaleByHotel);
  rationaleByHotel.set(hotelId, { nights, author: "designer" });
  return { ...baseline, rationaleByHotel };
}

export type Audience = "designer" | "client";

/**
 * The copy a stop card shows beneath the hotel details, chosen at render
 * time. Nothing here is written back into the itinerary or sent to the API.
 *
 * - `rationale`: the stop's rationale, unaltered. `stale` is set for the
 *   designer only, when the stop's nights no longer match the nights the
 *   text was written for.
 * - `about`: the hotel's supplied description, verbatim. Dataset content,
 *   not a recommendation.
 */
export type StopCopy =
  | { kind: "rationale"; text: string; stale: RationaleOrigin | null }
  | { kind: "about"; text: string }
  | { kind: "none" };

/**
 * Only the stop's hotel and night count are compared with the baseline. This
 * does not validate the claims inside the text, or what it says about other
 * stops.
 */
export function stopCopy(
  stop: ItineraryStop,
  baseline: Baseline,
  audience: Audience,
): StopCopy {
  const about: StopCopy = stop.hotel.description.trim()
    ? { kind: "about", text: stop.hotel.description }
    : { kind: "none" };

  // Empty after a designer swap: the model never chose this property.
  if (!stop.rationale.trim()) return about;

  // A non-empty rationale always belongs to the hotel it was written for,
  // because replacing a hotel clears it.
  const origin = baseline.rationaleByHotel.get(stop.hotel.id);
  const current = origin !== undefined && origin.nights === stop.nights;

  if (audience === "client") {
    return current
      ? { kind: "rationale", text: stop.rationale, stale: null }
      : about;
  }

  return {
    kind: "rationale",
    text: stop.rationale,
    stale: origin !== undefined && !current ? origin : null,
  };
}
