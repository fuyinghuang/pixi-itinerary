#!/usr/bin/env python3
"""Validate hotels.json against the dataset schema.

No external dependencies. Run with: python3 validate.py
Exits 0 on success, 1 on failure.

Tag vocabulary is read from _meta.tag_vocabulary inside the data file,
so the validator and data cannot drift apart.
"""

import json
import sys
from pathlib import Path

REQUIRED_HOTEL_FIELDS = {
    "id": str,
    "name": str,
    "country": str,
    "region": str,
    "city": str,
    "latitude": (int, float),
    "longitude": (int, float),
    "nearest_airport": dict,
    "description": str,
    "tags": list,
    "approx_nightly_rate": int,
    "currency": str,
    "images": list,
    "rooms": list,
}

OPTIONAL_HOTEL_FIELDS = {
    "access_notes": str,
}

REQUIRED_AIRPORT_FIELDS = {"iata": str, "name": str}
REQUIRED_ROOM_FIELDS = {"name": str, "rate_delta": int}

MIN_IMAGES = 3
MAX_IMAGES = 5


def validate(path: Path) -> list[str]:
    errors: list[str] = []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]
    except FileNotFoundError:
        return [f"File not found: {path}"]

    if not isinstance(data, dict):
        return ["Top-level value must be an object"]

    # --- _meta ---
    if "_meta" not in data:
        errors.append("Missing top-level '_meta' block")
        return errors

    meta = data["_meta"]
    if not isinstance(meta, dict):
        errors.append("'_meta' must be an object")
        return errors

    for key in ("version", "generated_for", "notes", "tag_vocabulary"):
        if key not in meta:
            errors.append(f"'_meta' missing field '{key}'")

    # Read tag vocabulary from _meta
    raw_vocab = meta.get("tag_vocabulary", [])
    if not isinstance(raw_vocab, list) or len(raw_vocab) == 0:
        errors.append("'_meta.tag_vocabulary' must be a non-empty array of strings")
        allowed_tags: set[str] = set()
    else:
        for i, entry in enumerate(raw_vocab):
            if not isinstance(entry, str):
                errors.append(
                    f"'_meta.tag_vocabulary[{i}]' must be a string, "
                    f"got {type(entry).__name__}"
                )
        allowed_tags = {t for t in raw_vocab if isinstance(t, str)}

    # --- hotels ---
    if "hotels" not in data:
        errors.append("Missing top-level 'hotels' array")
        return errors

    hotels = data["hotels"]
    if not isinstance(hotels, list):
        errors.append("'hotels' must be an array")
        return errors
    if len(hotels) == 0:
        errors.append("'hotels' array is empty")
        return errors

    ids_seen: set[str] = set()

    for i, hotel in enumerate(hotels):
        label = f"hotels[{i}] ({hotel.get('id', '???')})"

        if not isinstance(hotel, dict):
            errors.append(f"{label}: must be an object")
            continue

        # Required fields and types
        for field, expected in REQUIRED_HOTEL_FIELDS.items():
            if field not in hotel:
                errors.append(f"{label}: missing required field '{field}'")
                continue
            types = expected if isinstance(expected, tuple) else (expected,)
            if not isinstance(hotel[field], types):
                names = "/".join(t.__name__ for t in types)
                errors.append(
                    f"{label}: '{field}' should be {names}, "
                    f"got {type(hotel[field]).__name__}"
                )

        # brand must be string or null (present but nullable)
        if "brand" not in hotel:
            errors.append(f"{label}: missing required field 'brand'")
        elif hotel["brand"] is not None and not isinstance(hotel["brand"], str):
            errors.append(
                f"{label}: 'brand' must be a string or null, "
                f"got {type(hotel['brand']).__name__}"
            )

        # Optional fields — validate type when present
        for field, expected_type in OPTIONAL_HOTEL_FIELDS.items():
            if field in hotel and not isinstance(hotel[field], expected_type):
                errors.append(
                    f"{label}: '{field}' should be {expected_type.__name__} "
                    f"when present, got {type(hotel[field]).__name__}"
                )

        # Unique IDs
        hid = hotel.get("id")
        if isinstance(hid, str):
            if hid in ids_seen:
                errors.append(f"{label}: duplicate id '{hid}'")
            ids_seen.add(hid)

        # Tags from vocabulary
        tags = hotel.get("tags", [])
        if isinstance(tags, list):
            if len(tags) == 0:
                errors.append(f"{label}: 'tags' must not be empty")
            for tag in tags:
                if not isinstance(tag, str):
                    errors.append(
                        f"{label}: tag must be a string, "
                        f"got {type(tag).__name__}"
                    )
                elif allowed_tags and tag not in allowed_tags:
                    errors.append(f"{label}: unknown tag '{tag}'")

        # Lat/lng bounds
        lat = hotel.get("latitude")
        lng = hotel.get("longitude")
        if isinstance(lat, (int, float)) and not (-90 <= lat <= 90):
            errors.append(f"{label}: latitude {lat} out of range [-90, 90]")
        if isinstance(lng, (int, float)) and not (-180 <= lng <= 180):
            errors.append(f"{label}: longitude {lng} out of range [-180, 180]")

        # Images: 3-5 entries
        images = hotel.get("images", [])
        if isinstance(images, list):
            if len(images) < MIN_IMAGES:
                errors.append(
                    f"{label}: 'images' requires {MIN_IMAGES}-{MAX_IMAGES} "
                    f"entries, got {len(images)}"
                )
            elif len(images) > MAX_IMAGES:
                errors.append(
                    f"{label}: 'images' requires {MIN_IMAGES}-{MAX_IMAGES} "
                    f"entries, got {len(images)}"
                )

        # Airport sub-object
        airport = hotel.get("nearest_airport")
        if isinstance(airport, dict):
            for field, expected_type in REQUIRED_AIRPORT_FIELDS.items():
                if field not in airport:
                    errors.append(f"{label}: nearest_airport missing '{field}'")
                elif not isinstance(airport[field], expected_type):
                    errors.append(
                        f"{label}: nearest_airport.{field} should be "
                        f"{expected_type.__name__}"
                    )

        # Rooms: at least one
        rooms = hotel.get("rooms", [])
        if isinstance(rooms, list):
            if len(rooms) == 0:
                errors.append(f"{label}: 'rooms' must have at least one entry")
            for j, room in enumerate(rooms):
                rpfx = f"{label}.rooms[{j}]"
                if not isinstance(room, dict):
                    errors.append(f"{rpfx}: must be an object")
                    continue
                for field, expected_type in REQUIRED_ROOM_FIELDS.items():
                    if field not in room:
                        errors.append(f"{rpfx}: missing '{field}'")
                    elif not isinstance(room[field], expected_type):
                        errors.append(
                            f"{rpfx}: '{field}' should be "
                            f"{expected_type.__name__}"
                        )

        # Currency is 3-letter code
        currency = hotel.get("currency")
        if isinstance(currency, str) and len(currency) != 3:
            errors.append(
                f"{label}: 'currency' should be a 3-letter ISO 4217 code"
            )

    return errors


def main() -> None:
    path = Path(__file__).resolve().parent / "hotels.json"
    errors = validate(path)

    if errors:
        print(f"FAIL: {len(errors)} validation error(s)\n", file=sys.stderr)
        for err in errors:
            print(f"  \u2717 {err}", file=sys.stderr)
        sys.exit(1)

    # Summary statistics
    data = json.loads(path.read_text(encoding="utf-8"))
    hotels = data["hotels"]
    countries = sorted({h["country"] for h in hotels})
    all_tags: dict[str, int] = {}
    for h in hotels:
        for t in h.get("tags", []):
            all_tags[t] = all_tags.get(t, 0) + 1

    print(f"OK: {len(hotels)} hotels across {len(countries)} countries — all valid.")
    print(f"    Countries: {', '.join(countries)}")
    print(f"    Tags in use: {', '.join(f'{t} ({c})' for t, c in sorted(all_tags.items(), key=lambda x: -x[1]))}")

    pet_friendly = [h["name"] for h in hotels if "pet-friendly" in h.get("tags", [])]
    if pet_friendly:
        print(f"    Pet-friendly: {', '.join(pet_friendly)}")
    else:
        print("    Pet-friendly: none")


if __name__ == "__main__":
    main()
