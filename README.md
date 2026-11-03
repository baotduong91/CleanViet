# CleanViet · Four-day meal canvas

A flexible Monday–Thursday planner running at http://127.0.0.1:8017. Friday is the weekly gathering; weekends are meals out. Any cuisine or repeated dish is accepted. Commute badges are reminders rather than solver constraints.

## Use

1. Choose a Monday and press **Load week**.
2. Type any meal on each day. **Suggest ingredients** runs the local parser. Choose a target day in Family favorites for one-click suggestions; past confirmed meals appear in autocomplete.
3. Review ingredient names, quantities and units. Add or remove items freely. Edit each toddler note. Suggestions cover dinner for two adults and a toddler, without assumed leftover lunches.
4. Press **Confirm 4 dishes** to save and generate the combined shopping list.
5. Check items already covered by your pantry or purchased. Checked quantities are excluded from the remaining cost comparison. Reconfirm any meal edits before changing shopping checkboxes.
6. Use **Check Item / Supermarket Intel** for a specialty recommendation and estimated unit-price comparison. Use the moon/sun button for dark mode.

Changing the week date does not load a different canvas until **Load week** is pressed. Confirm edits before loading another week. Saved canvases and shopping checks persist in PostgreSQL. Unsaved form edits do not survive a reload. Revision checks prevent one tab from overwriting changes saved by another tab.

## Deploy / upgrade

```sh
docker compose up --build -d
```

Open http://127.0.0.1:8017. The seed service now applies `migrations/002_meal_canvas.sql`, an idempotent additive migration. Existing meal plans, pantry records and receipt tables are preserved as legacy records, and are not read or modified by the simplified planner. The old solver and inventory-execution APIs are retired. Existing PostgreSQL volume data is preserved. New installations initialize the simplified `schema.sql`; existing installations apply the same changes through the seed service. Do not delete the volume to upgrade.

The app and database remain bound to loopback. A non-root application container serves the React build and FastAPI routes. Same-origin write validation, input bounds and transaction-scoped save locking remain enabled.

## Ingredient parsing

`app/services/parser.py` implements a local, deterministic parser with bilingual ingredient aliases and dish patterns for the supplied examples. It runs without an external AI account. It is not a general-purpose LLM and cannot infer every ingredient in every dish: unknown names remain accepted and show a manual-entry prompt. All suggestions, quantities and toddler notes are editable. No cooking-time, repetition, cuisine or multi-day broth restrictions are imposed. Ingredients aggregate only across matching identities and compatible units; the app does not convert unlike units.

## Store recommendations and costs

`app/services/recommender.py` applies the requested household specialty archetypes:

- Đà Lạt / Mỹ Thuận: Vietnamese produce, herbs, calamansi and raw fish paste.
- Thuận Phát / Lucky Seafood: roe squid, whole fish and raw shrimp.
- Costco / Sam’s / Aldi: staple proteins, dairy, eggs and toddler fruit.
- Pantry / Weee!: dry noodles, wood ear, broth and sauces.

These are household heuristics, not verified rankings or current-stock claims. The displayed prices are planning benchmarks inherited from the original November 2, 2026 dataset, plus estimates for pasta, beef, broccoli, onion, broth and whole fish. The simplified dashboard compares unchecked required quantities with a Weee! benchmark using Decimal currency calculations. It excludes package overage, fees, fuel, takeout and unpriced custom items. Unknown ingredients go to the usual local supermarket with no fabricated price. A benchmark is used only when the requested unit matches its canonical unit. The simplified app does not yet edit benchmarks or use legacy receipt prices.

## Community review intelligence

The server supports the official **Google Places API (New)**. Set `GOOGLE_PLACES_API_KEY` in `.env`, enable Places API in the provider account, then recreate the app container:

```sh
docker compose up -d --force-recreate app
```

Only clicking **Check recent reviews** requests provider data. The request searches the representative named market and displays the returned place name, address and Google Maps link. Each review includes author attribution, review date and a source link. The analyzer filters the returned provider sample to the last 30 days and the requested seafood, produce, queues, cashier, smell and price keywords. Google supplies a limited review sample; no matching recent review does not mean no such reviews exist. The service does not persist provider review content.

Without a key, the UI explicitly reports that live reviews are unavailable. Provider failures also produce an explicit unavailable state. Specialty suggestions continue to work. No invented community badges, claimed stock confirmation, scraping bypasses or unsupported “fresh this week” statements are generated. Reviews are anecdotal and cannot establish current inventory or lowest price.

Implementation references: [Google Places Text Search](https://developers.google.com/maps/documentation/places/web-service/text-search), [field masks](https://developers.google.com/maps/documentation/places/web-service/choose-fields), and [review fields](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places).

## API

- `POST /api/meals/parse-ingredients` — `{ "dish_name": "Pasta bolognese" }`
- `GET /api/meals/history?q=pasta` — favorites and prior dish names.
- `GET /api/canvas?week_start=2026-11-02` — saved canvas, revision and current shopping aggregation.
- `PUT /api/canvas` — Monday date, current revision, four meals with unique Mon–Thu days, and checked item IDs.
- `GET /api/stores/intel?q=Mực%20trứng` — specialty and benchmark matches.
- `GET /api/stores/{store_id}/community` — on-demand review check; store IDs are `greens`, `seafood`, `bulk`, `pantry`, `manual`.
- `GET /api/health` — database readiness.

Interactive docs are at `/docs`; the local schema is `/openapi.json`.

## Development and validation

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock
pip install --no-deps -e .
docker compose up -d db
python seed_data.py
npm --prefix frontend ci
npm --prefix frontend run build
uvicorn app.main:app --host 127.0.0.1 --port 8017
```

For UI hot reload, `npm --prefix frontend run dev` proxies the API to port 8017. Production PWA assets use a new canvas cache version. The app requires the local API for loading and saving canvases; the service worker only caches static assets.

```sh
pytest -q
```

The database integration test requires a dedicated `cleanviet_test` database and refuses any other database name. Apply the migration to that database before running:

```sh
DATABASE_URL=postgresql+asyncpg://cleanviet:cleanviet_local_change_me@localhost:5436/cleanviet_test python seed_data.py
TEST_DATABASE_URL=postgresql+asyncpg://cleanviet:cleanviet_local_change_me@localhost:5436/cleanviet_test pytest -q
```

The integration test clears only the new canvas/history tables in the dedicated test database. It checks persistence, revision conflicts, shopping checks, autocomplete history and cross-origin write rejection. Unit tests cover ingredient extraction, unknown dishes, aggregation, unpriced unit mismatches, accented item lookup, recent-review filtering and missing-provider behavior.
