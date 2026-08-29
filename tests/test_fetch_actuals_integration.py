# same approach as test_fetch_forecast_integration.py - mocks the http
# call, writes to a real postgres

import os
import sys
from pathlib import Path
from unittest.mock import patch

import psycopg2
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

DSN = os.environ.get("WAREHOUSE_DB_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="WAREHOUSE_DB_DSN not set")

# one resolved day, one still-null day (ERA5 hasn't caught up to it yet)
FAKE_RESPONSE = {
    "daily": {
        "time": ["2026-08-14", "2026-08-15"],
        "temperature_2m_max": [22.3, None],
        "temperature_2m_min": [15.1, None],
        "precipitation_sum": [0.0, None],
        "weather_code": [1, None],
    }
}


@pytest.fixture
def conn():
    c = psycopg2.connect(DSN)
    with c.cursor() as cur:
        cur.execute("DELETE FROM raw.actuals_daily WHERE city = 'TestCity';")
    c.commit()
    yield c
    with c.cursor() as cur:
        cur.execute("DELETE FROM raw.actuals_daily WHERE city = 'TestCity';")
    c.commit()
    c.close()


def test_null_days_are_skipped_not_written(conn):
    from fetch_actuals import load_actuals_range

    with patch("fetch_actuals.CITIES", [{"city": "TestCity", "state": "XX", "latitude": 0.0, "longitude": 0.0}]):
        with patch("fetch_actuals.get_actuals", return_value=FAKE_RESPONSE):
            loaded = load_actuals_range(conn, "2026-08-14", "2026-08-15")

    assert loaded == 1  # only the resolved day counted

    with conn.cursor() as cur:
        cur.execute("SELECT target_date, temperature_2m_max FROM raw.actuals_daily WHERE city = 'TestCity';")
        rows = cur.fetchall()

    assert len(rows) == 1
    assert str(rows[0][0]) == "2026-08-14"
    assert rows[0][1] == 22.3


def test_resweep_fills_in_a_previously_null_day(conn):
    from fetch_actuals import load_actuals_range

    with patch("fetch_actuals.CITIES", [{"city": "TestCity", "state": "XX", "latitude": 0.0, "longitude": 0.0}]):
        with patch("fetch_actuals.get_actuals", return_value=FAKE_RESPONSE):
            load_actuals_range(conn, "2026-08-14", "2026-08-15")  # first sweep: day 2 still null

        # simulate ERA5 catching up: day 2 now has real data
        resolved_response = {
            "daily": {
                "time": ["2026-08-14", "2026-08-15"],
                "temperature_2m_max": [22.3, 19.8],
                "temperature_2m_min": [15.1, 14.0],
                "precipitation_sum": [0.0, 2.4],
                "weather_code": [1, 61],
            }
        }
        with patch("fetch_actuals.get_actuals", return_value=resolved_response):
            load_actuals_range(conn, "2026-08-14", "2026-08-15")  # second sweep picks it up

    with conn.cursor() as cur:
        cur.execute("SELECT target_date, temperature_2m_max FROM raw.actuals_daily WHERE city = 'TestCity' ORDER BY target_date;")
        rows = cur.fetchall()

    assert len(rows) == 2
    assert rows[1][1] == 19.8  # day 2 is no longer missing
