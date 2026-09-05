# Weather Forecast Accuracy Tracker

Tracks how accurate weather forecasts actually are at different lead times - is a 1-day-out forecast really better than a 7-day-out one, and does it vary by city? Airflow pulls daily forecasts and actuals from [Open-Meteo](https://open-meteo.com) (free, no key needed) into Postgres, dbt turns that into accuracy numbers, and a dashboard shows the result.

**Status:** infra, forecast extraction, actuals extraction, and the dbt models are done and tested. Dashboard is next.

## Design notes

- Two separate Postgres containers - one for Airflow's own metadata, one for the actual weather data. Keeps them from getting tangled together.
- `raw.forecast_daily` has a unique constraint on (city, forecast_made_on, target_date), so re-running the DAG after a failure overwrites that day instead of creating duplicates. Tested against a real Postgres instance in `tests/`, not just assumed.
- The forecast DAG has `catchup=False` on purpose - "today's forecast" only makes sense on the day it's fetched, there's no way to backfill what the API would've said in the past. Actuals come from a separate DAG hitting the historical/reanalysis endpoint, which can be backfilled.
- The actuals DAG re-sweeps a trailing 14-day window (ending 7 days back, past ERA5's processing lag) instead of just grabbing "yesterday". A day that's still unresolved gets skipped rather than written as null, and picked up automatically on a later sweep once it resolves - tested in `tests/test_fetch_actuals_integration.py`, including the "previously-null day gets filled in" case specifically.
- **Why there's a separate `backfill_forecasts.py`:** the live forecast DAG only fetches *today's* forecast for future dates, and the actuals backfill only covers *past* dates - so right after initial setup there's a real gap with zero overlapping dates for the accuracy join, and the marts come back empty. `backfill_forecasts.py` fixes this by pulling 90 days of *historical* forecasts at real 1-7 day lead times from Open-Meteo's Previous Runs API, landing them in the same `raw.forecast_daily` table the live DAG uses - so there's meaningful overlap with the actuals backfill immediately, instead of waiting ~1-2 weeks for today's live forecasts to actually resolve.

## Architecture

```
Open-Meteo Forecast API ──▶ fetch_forecast_dag (daily) ──▶ raw.forecast_daily
Open-Meteo Historical API ─▶ fetch_actuals_dag (next)   ──▶ raw.actuals_daily
                                                              │
                                                              ▼
                                                     dbt (staging → marts)
                                                              │
                                                              ▼
                                                   accuracy-by-lead-time dashboard
```

## Running it

```
cp .env.example .env
docker compose up -d
```

- Airflow: http://localhost:8080 (admin/admin by default)
- Warehouse Postgres: localhost:5433

Unpause `fetch_forecast_daily` in the UI and trigger it manually to load today's data right away. It'll otherwise run every morning at 13:00 UTC.

## Tests

```
pip install -r requirements.txt

# fast, no network or db needed
pytest tests/test_open_meteo_client.py -v

# needs a real postgres with init_db.sql applied
WAREHOUSE_DB_DSN=postgresql://weather:weather@localhost:5433/weather pytest tests/ -v
```

## dbt

```bash
pip install -r requirements.txt
cd dbt/weather_accuracy
export DBT_PROFILES_DIR=$(pwd)
dbt run
dbt test
```

Connects to `localhost:5433` by default (the warehouse Postgres exposed by Docker Compose), same credentials as `.env`. `mart_accuracy_by_lead_time` is the headline table — average forecast error grouped by how many days out the forecast was made.

## Layout

```
dags/     airflow DAGs
scripts/  extraction code + open-meteo client + db schema
tests/    unit tests (no network) + integration tests (real postgres)
dbt/      dbt models (coming next)
```

## Roadmap

- [x] Docker Compose infra
- [x] City list (12 cities, mixed climates)
- [x] Forecast extraction + idempotent upsert + daily DAG + tests
- [x] Actuals extraction from the historical API, sweeping a trailing window to handle the ERA5 lag
- [x] Backfill script to seed 90 days of history in one shot instead of waiting weeks
- [x] Historical forecast backfill (Previous Runs API) so the accuracy marts have real overlapping data immediately
- [x] dbt: staging → intermediate (forecast/actual join + error calc) → marts, with tests
- [ ] CI running tests + dbt test on push
- [ ] Dashboard
- [ ] Switch dbt models to incremental once the raw tables get big

## Data source

[Open-Meteo](https://open-meteo.com) - free, no API key, CC BY 4.0. Up to 10,000 requests/day on the free tier.
