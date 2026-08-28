# mocks the http call but writes to a real postgres, so this actually
# proves the python and the SQL agree with each other
#
# needs WAREHOUSE_DB_DSN pointing at a postgres with init_db.sql applied,
# skips itself if that's not set

import os
import sys
from pathlib import Path
from unittest.mock import patch

import psycopg2
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

DSN = os.environ.get("WAREHOUSE_DB_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="WAREHOUSE_DB_DSN not set")

FAKE_RESPONSE = {
    "daily": {
        "time": ["2026-08-27", "2026-08-28"],
        "temperature_2m_max": [24.1, 25.6],
        "temperature_2m_min": [18.2, 18.9],
        "precipitation_sum": [0.0, 0.0],
        "precipitation_probability_max": [5, 5],
        "weather_code": [0, 1],
    }
}


@pytest.fixture
def conn():
    c = psycopg2.connect(DSN)
    with c.cursor() as cur:
        cur.execute("DELETE FROM raw.forecast_daily WHERE city = 'TestCity';")
    c.commit()
    yield c
    with c.cursor() as cur:
        cur.execute("DELETE FROM raw.forecast_daily WHERE city = 'TestCity';")
    c.commit()
    c.close()


def test_fetch_and_load_writes_expected_rows(conn):
    from fetch_forecast import fetch_and_load

    with patch("fetch_forecast.CITIES", [{"city": "TestCity", "state": "XX", "latitude": 0.0, "longitude": 0.0}]):
        with patch("fetch_forecast.get_forecast", return_value=FAKE_RESPONSE):
            loaded = fetch_and_load(conn, forecast_made_on="2026-08-27")

    assert loaded == 2

    with conn.cursor() as cur:
        cur.execute(
            "SELECT target_date, temperature_2m_max FROM raw.forecast_daily "
            "WHERE city = 'TestCity' ORDER BY target_date;"
        )
        rows = cur.fetchall()

    assert len(rows) == 2
    assert str(rows[0][0]) == "2026-08-27" and rows[0][1] == 24.1
    assert str(rows[1][0]) == "2026-08-28" and rows[1][1] == 25.6


def test_rerunning_same_day_overwrites_not_duplicates(conn):
    from fetch_forecast import fetch_and_load

    with patch("fetch_forecast.CITIES", [{"city": "TestCity", "state": "XX", "latitude": 0.0, "longitude": 0.0}]):
        with patch("fetch_forecast.get_forecast", return_value=FAKE_RESPONSE):
            fetch_and_load(conn, forecast_made_on="2026-08-27")
            fetch_and_load(conn, forecast_made_on="2026-08-27")  # simulate a retry

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw.forecast_daily WHERE city = 'TestCity';")
        (count,) = cur.fetchone()

    assert count == 2
