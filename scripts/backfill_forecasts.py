# backfills historical forecasts (at real 1-7 day lead times) using
# open-meteo's previous-runs-api, so the accuracy marts have real
# overlapping forecast/actual data immediately instead of waiting
# ~1-2 weeks for today's live forecasts to actually resolve
#
#   docker compose exec airflow-scheduler python /opt/airflow/scripts/backfill_forecasts.py
#
# writes into the same raw.forecast_daily table and reuses the same
# upsert as the daily live fetch - lead_time_days is derived downstream
# in dbt from (target_date - forecast_made_on), so no schema changes needed

import logging
import os

import psycopg2

from cities import CITIES
from open_meteo_client import get_previous_runs, aggregate_previous_runs_to_daily
from fetch_forecast import UPSERT_SQL

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PAST_DAYS = 90


def main():
    dsn = os.environ["WAREHOUSE_DB_DSN"]
    conn = psycopg2.connect(dsn)
    total = 0
    try:
        with conn.cursor() as cur:
            for c in CITIES:
                try:
                    payload = get_previous_runs(c["latitude"], c["longitude"], past_days=PAST_DAYS)
                except Exception:
                    logger.exception("failed to fetch previous runs for %s, skipping", c["city"])
                    continue

                rows = aggregate_previous_runs_to_daily(
                    payload,
                    extra_fields={
                        "city": c["city"],
                        "state": c["state"],
                        "latitude": c["latitude"],
                        "longitude": c["longitude"],
                    },
                )
                for row in rows:
                    cur.execute(UPSERT_SQL, row)

                total += len(rows)
                logger.info("loaded %d historical forecast rows for %s", len(rows), c["city"])

        conn.commit()
        logger.info("backfill done, %d rows loaded", total)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
