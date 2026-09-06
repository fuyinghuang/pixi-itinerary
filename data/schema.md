# Hotel Dataset Schema

## Top-level structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_meta` | object | Yes | Dataset metadata — see [Meta block](#meta-block) |
| `hotels` | array of [Hotel](#hotel-object) | Yes | Non-empty array of hotel records |

## Meta block

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Semver of the dataset format |
| `generated_for` | string | Purpose label |
| `notes` | array of string | Caveats about the data (rates, images, descriptions) |
| `tag_vocabulary` | array of string | The canonical set of allowed tag values — every tag used in any hotel record must appear here |

## Hotel object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Stable slug, unique across the dataset. Kebab-case, no spaces. Used as the primary key. |
| `name` | string | Yes | Display name of the property |
| `brand` | string or null | Yes | Parent hotel group (e.g. `"Belmond"`, `"Hyatt"`). `null` for independent properties — not an empty string. |
| `country` | string | Yes | Country name in English |
| `region` | string | Yes | Sub-national region, state, or province |
| `city` | string | Yes | City, town, or locality name |
| `latitude` | number | Yes | Decimal degrees, WGS 84. Range: -90 to 90. |
| `longitude` | number | Yes | Decimal degrees, WGS 84. Range: -180 to 180. |
| `nearest_airport` | [Airport](#airport-object) | Yes | Primary commercial airport for guest arrivals — the airport candidates would search flights to |
| `access_notes` | string | No | How guests reach the property from the nearest airport. Include when the transfer involves a mode change (charter flight, boat), takes more than 60 minutes, or has important routing caveats. Omit for straightforward airport-to-hotel drives. |
| `description` | string | Yes | 2-3 sentence property description written for a travel designer audience |
| `tags` | array of string | Yes | One or more values from the [tag vocabulary](#tag-vocabulary). Non-empty. |
| `approx_nightly_rate` | integer | Yes | Indicative starting rate per night. See `currency`. |
| `currency` | string | Yes | ISO 4217 currency code (all entries in this dataset use `"USD"`) |
| `images` | array of string | Yes | 3-5 placeholder image URLs |
| `rooms` | array of [Room](#room-object) | Yes | At least one room/villa category |

## Airport object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `iata` | string | Yes | Three-letter IATA airport code |
| `name` | string | Yes | Full airport name |

For remote properties (safari lodges, island resorts), `nearest_airport` is the international gateway guests fly into. The `access_notes` field on the parent hotel object describes the onward transfer — charter flights, bush airstrips, boat connections, etc. This separation keeps `nearest_airport` consistently useful for flight search APIs while `access_notes` captures the human routing context.

## Room object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Room or villa category name |
| `rate_delta` | integer | Yes | Additional cost per night above the property's `approx_nightly_rate`. The base category has `rate_delta: 0`. |

## Tag vocabulary

Tags are drawn from a controlled vocabulary defined in `_meta.tag_vocabulary`. Every tag in a hotel's `tags` array must appear in that vocabulary. The vocabulary is the canonical superset — not every tag needs to be used in the current dataset.

| Tag | Meaning |
|-----|---------|
| `luxury` | Five-star or equivalent service level |
| `boutique` | Small, design-led property (typically under 50 rooms) |
| `city` | Urban location — walkable to city attractions |
| `beach` | Beachfront or private-island property |
| `safari` | Wildlife-focused lodge or camp |
| `spa` | Significant spa or wellness facility on-site |
| `resort` | Self-contained resort with multiple facilities |
| `family` | Welcomes children with appropriate facilities |
| `adults-only` | Restricted to adult guests |
| `pet-friendly` | Accepts guest pets — verified against official or credible third-party sources |
| `eco` | Demonstrated sustainability or conservation commitment |
| `all-inclusive` | Nightly rate bundles meals, beverages, and/or activities |
| `heritage` | Historic building or culturally significant property |
| `wellness` | Programmes beyond a standard spa — retreats, holistic health, etc. |

## Notes

- **Rates** are indicative 2025 averages. Real rates vary by season, room type, and booking channel.
- **Images** are deterministic placeholders (`picsum.photos/seed/{slug}/800/600`), not real hotel photography.
- **Coordinates** are verified to within approximately one kilometre for most properties. Safari lodge coordinates carry lower confidence due to limited public data.
- **brand** is `null` for independent properties, not an empty string.
- **access_notes** is present on all hotels in this dataset for convenience, but the field is optional in the schema — future additions may omit it for simple airport-to-hotel transfers.
