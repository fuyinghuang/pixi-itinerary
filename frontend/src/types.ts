/**
 * The API contract, mirrored by hand from `backend/app/schemas.py`.
 *
 * The Pydantic schemas are canonical. When the contract changes, this file
 * changes in the same commit. There is no code generation.
 */

export type TripRegion = "south-africa" | "east-africa" | "japan" | "italy";
export type TripLengthUnit = "days" | "nights";

export interface TripLength {
  value: number;
  unit: TripLengthUnit;
}

export interface Airport {
  iata: string;
  name: string;
}

export interface Room {
  name: string;
  rate_delta: number;
}

/** One property, exactly as supplied by the catalogue. */
export interface Hotel {
  id: string;
  name: string;
  brand: string | null;
  country: string;
  /** Sub-national — "Western Cape", "Kanto". Not a TripRegion. */
  region: string;
  city: string;
  latitude: number;
  longitude: number;
  nearest_airport: Airport;
  description: string;
  tags: string[];
  approx_nightly_rate: number;
  currency: string;
  /** Three to five. Never assume a count. */
  images: string[];
  rooms: Room[];
  /** Supplied access information. Authoritative; never paraphrased here. */
  access_notes: string | null;
}

/** A property the designer could swap in. Unused until the edit slice. */
export interface HotelOption {
  id: string;
  name: string;
  city: string;
}

export interface ItineraryStop {
  day_from: number;
  day_to: number;
  nights: number;
  rationale: string;
  hotel: Hotel;
  subtotal: number;
  replacement_options: HotelOption[];
}

export interface Itinerary {
  interpreted_brief: string;
  narrative: string;
  trip_region: TripRegion;
  trip_length: TripLength;
  accommodation_nights: number;
  total_days: number;
  currency: "USD";
  accommodation_total: number;
  price_note: string;
  stops: ItineraryStop[];
}

/** A normal product outcome, returned with HTTP 200. */
export interface UnsupportedBriefResponse {
  interpreted_brief: string;
  reason: string;
  suggested_regions: TripRegion[];
  supported_regions: TripRegion[];
}

/** One stop as the designer has edited it. */
export interface RecomputeStop {
  hotel_id: string;
  nights: number;
  rationale: string;
}

/**
 * A designer edit. Only the fields the designer owns are sent — prices,
 * day numbers and hotel content are recomputed from the catalogue.
 *
 * The trip length is carried as a unit alone. Changing a stop's nights is
 * allowed to change how long the trip is, so the backend derives the new
 * length from the edited stops rather than trusting a value from here.
 */
export interface RecomputeRequest {
  trip_region: TripRegion;
  trip_length_unit: TripLengthUnit;
  interpreted_brief: string;
  narrative: string;
  stops: RecomputeStop[];
}

export interface ErrorResponse {
  code: "planner_unavailable" | "planner_invalid_output" | "invalid_request";
  message: string;
  retryable: boolean;
}

export type GenerateResult = Itinerary | UnsupportedBriefResponse;

/**
 * Both outcomes arrive at HTTP 200 and neither carries a discriminator
 * field, so the client narrows structurally. One place, one check.
 */
export function isItinerary(result: GenerateResult): result is Itinerary {
  return "stops" in result;
}

export const REGION_LABELS: Record<TripRegion, string> = {
  "south-africa": "South Africa",
  "east-africa": "East Africa",
  japan: "Japan",
  italy: "Italy",
};
