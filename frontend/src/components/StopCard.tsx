import { useId, useState } from "react";

import type { StopCopy } from "../baseline";
import type { ItineraryStop } from "../types";

/** Matches `RecomputeStop.rationale` in the backend schema. */
const RATIONALE_MAX_LENGTH = 600;

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
  /** What to show beneath the hotel details, already chosen for this view. */
  copy: StopCopy;
  currency: string;
  /** Edits are disabled while a recompute is in flight. */
  busy: boolean;
  /** The client sees the itinerary, not the tools used to build it. */
  preview: boolean;
  onNightsChange: (nights: number) => void;
  onReplace: (hotelId: string) => void;
  /** Resolves to whether the save succeeded. */
  onRationaleSave: (rationale: string) => Promise<boolean>;
}

export default function StopCard({
  stop,
  copy,
  currency,
  busy,
  preview,
  onNightsChange,
  onReplace,
  onRationaleSave,
}: Props) {
  const { hotel } = stop;
  const alternatives = stop.replacement_options;
  /** The designer's unsaved rewrite of the rationale; null when not editing. */
  const [draft, setDraft] = useState<string | null>(null);
  const draftId = useId();

  async function saveDraft() {
    if (draft === null || !draft.trim()) return;
    // Closed only once the save succeeds, so a failure keeps the text.
    if (await onRationaleSave(draft.trim())) setDraft(null);
  }

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

        {!preview && (
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
        )}

        {/* The rationale, unaltered. When the stay no longer matches what it
            was written for, the designer sees why it is marked and can review
            it; the client is shown the hotel's description instead. */}
        {copy.kind === "rationale" && (preview || draft === null) && (
          <div className="rationale">
            {!preview && copy.stale && (
              <p className="rationale-note">
                Written for {copy.stale.author === "model" ? "the original " : ""}
                {nightCount(copy.stale.nights)}.{" "}
                <button
                  type="button"
                  className="link"
                  onClick={() => setDraft(copy.text)}
                  disabled={busy}
                >
                  Review description
                </button>
              </p>
            )}
            <p>{copy.text}</p>
          </div>
        )}

        {/* Designer only. Nothing reaches the client until the save succeeds. */}
        {!preview && draft !== null && (
          <div className="rationale-editor">
            <label htmlFor={draftId}>
              Description for {nightCount(stop.nights)}
            </label>
            <textarea
              id={draftId}
              value={draft}
              maxLength={RATIONALE_MAX_LENGTH}
              disabled={busy}
              onChange={(event) => setDraft(event.target.value)}
            />
            {/* Saving records who confirmed the text and for how many nights.
                It does not read the text, so the hint says so. */}
            <p className="rationale-editor-hint">
              Check the text matches {nightCount(stop.nights)} — saving doesn't
              check the wording. Until you save, the client preview shows the
              hotel's description.
            </p>
            <div className="rationale-editor-actions">
              <button
                type="button"
                onClick={() => void saveDraft()}
                disabled={busy || !draft.trim()}
              >
                Save for {nightCount(stop.nights)}
              </button>
              <button
                type="button"
                className="link"
                onClick={() => setDraft(null)}
                disabled={busy}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Supplied verbatim from the dataset — not a recommendation. */}
        {copy.kind === "about" && (
          <p className="about-hotel">
            <span>About the hotel</span>
            {copy.text}
          </p>
        )}

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
