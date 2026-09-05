# proves backfill_forecasts actually writes valid rows to postgres -
# mocks the http call, but the SQL execution and NULL handling for
# weather_code/precipitation_probability_max is real

import os
import sys
from pathlib import Path
from unittest.mock import patch

import psycopg2
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

DSN = os.environ.get("WAREHOUSE_DB_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="WAREHOUSE_DB_DSN not set")


def _fixture():
    times = [f"2026-08-20T{h:02d}:00" for h in range(24)]
    return {
        "hourly": {
            "time": times,
            "temperature_2m_previous_day1": [15.0] * 24,
            "precipitation_previous_day1": [0.0] * 24,
        }
    }


@pytest.fixture
def conn():
    c = psycopg2.connect(DSN)
    with c.cursor() as cur:
        cur.execute("DELETE FROM raw.forecast_daily WHERE city = 'BackfillTestCity';")
    c.commit()
    yield c
    with c.cursor() as cur:
        cur.execute("DELETE FROM raw.forecast_daily WHERE city = 'BackfillTestCity';")
    c.commit()
    c.close()


def test_backfill_writes_row_with_null_weather_code(conn):
    import backfill_forecasts

    with patch("backfill_forecasts.CITIES", [{"city": "BackfillTestCity", "state": "XX", "latitude": 0.0, "longitude": 0.0}]):
        with patch("backfill_forecasts.get_previous_runs", return_value=_fixture()):
            backfill_forecasts.main()

    with conn.cursor() as cur:
        cur.execute(
            "SELECT target_date, forecast_made_on, temperature_2m_max, weather_code "
            "FROM raw.forecast_daily WHERE city = 'BackfillTestCity';"
        )
        rows = cur.fetchall()

    assert len(rows) == 1
    assert str(rows[0][0]) == "2026-08-20"
    assert str(rows[0][1]) == "2026-08-19"
    assert rows[0][2] == 15.0
    assert rows[0][3] is None  # weather_code intentionally not backfilled
