# run this once, manually, to seed months of history instead of waiting
# for the daily DAG to accumulate it one window at a time
#
#   docker compose exec airflow-scheduler python /opt/airflow/scripts/backfill_actuals.py
#
# safe to re-run - same upsert as the daily sweep

import logging
import os
from datetime import date, timedelta

import psycopg2

from fetch_actuals import LAG_DAYS, load_actuals_range

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BACKFILL_DAYS = 90


def main():
    dsn = os.environ["WAREHOUSE_DB_DSN"]
    end_date = date.today() - timedelta(days=LAG_DAYS)
    start_date = end_date - timedelta(days=BACKFILL_DAYS)

    conn = psycopg2.connect(dsn)
    try:
        total = load_actuals_range(conn, str(start_date), str(end_date))
        logging.info("backfill done, %d rows loaded for %s to %s", total, start_date, end_date)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
