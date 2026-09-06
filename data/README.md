# Hotel Seed Dataset

Fixture data for the PIXI AI Product Engineer take-home exercise.

## What's here

| File | Purpose |
|------|---------|
| `hotels.json` | Luxury hotel dataset — the canonical fixture |
| `schema.md` | Field-by-field documentation, tag vocabulary, and access_notes conventions |
| `validate.py` | Validation script — checks every record against the schema |

## Quick start

```bash
python3 validate.py
```

The script has no external dependencies. It reads the tag vocabulary from `_meta.tag_vocabulary` inside the data file so the two cannot drift apart. Exits 0 on success, 1 on failure, and prints every violation it finds.

## What this is

A curated set of well-known luxury properties spread across South Africa, East Africa, Japan, and Italy. Each country has multiple properties that pair into realistic multi-stop itineraries — city to safari, coast to highlands, or cross-border circuits.

- Hotel names and locations are real
- Descriptions are original — not sourced from hotel websites
- Images are placeholder URLs (picsum.photos with deterministic seeds)
- Nightly rates are indicative averages, not live pricing
- Transfer routing (`access_notes`) reflects how luxury guests actually reach each property

## For candidates

You may extend this dataset (add hotels, add fields, restructure for your stack) but you shouldn't need to. The data is framework-agnostic — import it into Django, FastAPI, a vector store, or whatever your approach requires.

See `schema.md` for the full field reference and tag vocabulary.
