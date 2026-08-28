# Weather Forecast Accuracy Tracker

Tracks how accurate weather forecasts actually are at different lead times - is a 1-day-out forecast really better than a 7-day-out one, and does it vary by city? Airflow pulls daily forecasts and actuals from [Open-Meteo](https://open-meteo.com) (free, no key needed) into Postgres, dbt turns that into accuracy numbers, and a dashboard shows the result.

**Status:** infra + forecast extraction are done and tested. Actuals extraction, dbt models, and the dashboard are next.

## Design notes

- Two separate Postgres containers - one for Airflow's own metadata, one for the actual weather data. Keeps them from getting tangled together.
- `raw.forecast_daily` has a unique constraint on (city, forecast_made_on, target_date), so re-running the DAG after a failure overwrites that day instead of creating duplicates. Tested against a real Postgres instance in `tests/`, not just assumed.
- The forecast DAG has `catchup=False` on purpose - "today's forecast" only makes sense on the day it's fetched, there's no way to backfill what the API would've said in the past. Actuals come from a separate DAG hitting the historical/reanalysis endpoint, which can be backfilled.

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
- [ ] Actuals extraction from the historical API (handling the ERA5 lag)
- [ ] Backfill from Open-Meteo's forecast archive so there's data from day one
- [ ] dbt: staging → intermediate (forecast/actual join + error calc) → marts
- [ ] CI running tests + dbt test on push
- [ ] Dashboard
- [ ] Switch dbt models to incremental once the raw tables get big

## Data source

[Open-Meteo](https://open-meteo.com) - free, no API key, CC BY 4.0. Up to 10,000 requests/day on the free tier.
