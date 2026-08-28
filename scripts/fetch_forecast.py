# pulls today's forecast for every city and upserts into raw.forecast_daily
# re-running this for the same day just overwrites, doesn't duplicate
# (see the unique constraint on city/forecast_made_on/target_date)

import logging
import os
from datetime import date

import psycopg2

from cities import CITIES
from open_meteo_client import get_forecast, parse_daily_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

UPSERT_SQL = """
    INSERT INTO raw.forecast_daily (
        city, state, latitude, longitude,
        forecast_made_on, target_date,
        temperature_2m_max, temperature_2m_min,
        precipitation_sum, precipitation_probability_max, weather_code
    )
    VALUES (
        %(city)s, %(state)s, %(latitude)s, %(longitude)s,
        %(forecast_made_on)s, %(target_date)s,
        %(temperature_2m_max)s, %(temperature_2m_min)s,
        %(precipitation_sum)s, %(precipitation_probability_max)s, %(weather_code)s
    )
    ON CONFLICT (city, forecast_made_on, target_date) DO UPDATE SET
        temperature_2m_max = EXCLUDED.temperature_2m_max,
        temperature_2m_min = EXCLUDED.temperature_2m_min,
        precipitation_sum = EXCLUDED.precipitation_sum,
        precipitation_probability_max = EXCLUDED.precipitation_probability_max,
        weather_code = EXCLUDED.weather_code,
        inserted_at = now();
"""


def fetch_and_load(conn, forecast_made_on):
    rows_loaded = 0
    with conn.cursor() as cur:
        for c in CITIES:
            try:
                payload = get_forecast(c["latitude"], c["longitude"])
            except Exception:
                logger.exception("failed to fetch %s, skipping", c["city"])
                continue

            rows = parse_daily_response(
                payload,
                extra_fields={
                    "city": c["city"],
                    "state": c["state"],
                    "latitude": c["latitude"],
                    "longitude": c["longitude"],
                    "forecast_made_on": forecast_made_on,
                },
            )
            for row in rows:
                row.setdefault("precipitation_probability_max", None)
                cur.execute(UPSERT_SQL, row)

            rows_loaded += len(rows)
            logger.info("loaded %d rows for %s", len(rows), c["city"])

    conn.commit()
    return rows_loaded


def main():
    dsn = os.environ["WAREHOUSE_DB_DSN"]
    forecast_made_on = str(date.today())
    conn = psycopg2.connect(dsn)
    try:
        total = fetch_and_load(conn, forecast_made_on)
        logger.info("done, %d rows loaded for %s", total, forecast_made_on)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
