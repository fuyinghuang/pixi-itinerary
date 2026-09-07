/**
 * The backend client.
 *
 * Only the generation path exists in this slice. Recompute arrives with the
 * edit controls that need it.
 */

import type { ErrorResponse, GenerateResult } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** A failure the UI can present, and sometimes offer to retry. */
export class ApiError extends Error {
  readonly code: ErrorResponse["code"] | "network";
  readonly retryable: boolean;

  constructor(message: string, code: ApiError["code"], retryable: boolean) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.retryable = retryable;
  }
}

const UNREACHABLE =
  "Could not reach the itinerary service. Check that the backend is running.";

async function toApiError(response: Response): Promise<ApiError> {
  // The backend sends a typed ErrorResponse, but a proxy or a crash may not.
  try {
    const body = (await response.json()) as Partial<ErrorResponse>;
    if (body?.message && body?.code) {
      return new ApiError(body.message, body.code, body.retryable ?? false);
    }
  } catch {
    // Fall through to the generic message below.
  }
  return new ApiError(
    `The itinerary service returned ${response.status}.`,
    "planner_unavailable",
    response.status >= 500,
  );
}

/**
 * Turn a client brief into an itinerary.
 *
 * Resolves to an `Itinerary`, or to an `UnsupportedBriefResponse` when the
 * catalogue cannot serve the destination — that is a successful outcome,
 * not an error. Rejects with `ApiError` when the service fails.
 */
export async function generateItinerary(
  brief: string,
  signal?: AbortSignal,
): Promise<GenerateResult> {
  let response: Response;

  try {
    response = await fetch(`${BASE_URL}/api/itineraries`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ brief }),
      signal,
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError(UNREACHABLE, "network", true);
  }

  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as GenerateResult;
}
