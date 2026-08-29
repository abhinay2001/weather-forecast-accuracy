# pulls actual observed weather (ERA5 reanalysis) and upserts into
# raw.actuals_daily
#
# ERA5 has a ~5-7 day processing lag, so this sweeps a trailing window
# ending 7 days back rather than just "yesterday". re-sweeping the same
# window daily means any date that was still null last time gets picked
# up automatically once it resolves - no need to track which exact
# date became available.

import logging
import os
from datetime import date, timedelta

import psycopg2

from cities import CITIES
from open_meteo_client import get_actuals, parse_daily_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

LAG_DAYS = 7       # don't ask for anything more recent than this
WINDOW_DAYS = 14    # how far back the daily sweep re-checks

UPSERT_SQL = """
    INSERT INTO raw.actuals_daily (
        city, state, latitude, longitude, target_date,
        temperature_2m_max, temperature_2m_min, precipitation_sum, weather_code
    )
    VALUES (
        %(city)s, %(state)s, %(latitude)s, %(longitude)s, %(target_date)s,
        %(temperature_2m_max)s, %(temperature_2m_min)s, %(precipitation_sum)s, %(weather_code)s
    )
    ON CONFLICT (city, target_date) DO UPDATE SET
        temperature_2m_max = EXCLUDED.temperature_2m_max,
        temperature_2m_min = EXCLUDED.temperature_2m_min,
        precipitation_sum = EXCLUDED.precipitation_sum,
        weather_code = EXCLUDED.weather_code,
        inserted_at = now();
"""


def load_actuals_range(conn, start_date, end_date):
    """Fetch + upsert actuals for every city over [start_date, end_date]. Rows still null (not resolved yet) are skipped."""
    rows_loaded = 0
    with conn.cursor() as cur:
        for c in CITIES:
            try:
                payload = get_actuals(c["latitude"], c["longitude"], start_date, end_date)
            except Exception:
                logger.exception("failed to fetch actuals for %s, skipping", c["city"])
                continue

            rows = parse_daily_response(
                payload,
                extra_fields={
                    "city": c["city"],
                    "state": c["state"],
                    "latitude": c["latitude"],
                    "longitude": c["longitude"],
                },
            )
            # skip days ERA5 hasn't resolved yet instead of writing nulls
            rows = [r for r in rows if r.get("temperature_2m_max") is not None]

            for row in rows:
                cur.execute(UPSERT_SQL, row)

            rows_loaded += len(rows)
            logger.info("loaded %d actual rows for %s", len(rows), c["city"])

    conn.commit()
    return rows_loaded


def main():
    dsn = os.environ["WAREHOUSE_DB_DSN"]
    end_date = date.today() - timedelta(days=LAG_DAYS)
    start_date = end_date - timedelta(days=WINDOW_DAYS)

    conn = psycopg2.connect(dsn)
    try:
        total = load_actuals_range(conn, str(start_date), str(end_date))
        logger.info("done, %d rows loaded for %s to %s", total, start_date, end_date)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
