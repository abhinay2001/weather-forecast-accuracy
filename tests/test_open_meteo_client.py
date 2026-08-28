# tests parse_daily_response against a fixture shaped like open-meteo's
# real response format - no network needed

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from open_meteo_client import parse_daily_response  # noqa: E402

SAMPLE_FORECAST_RESPONSE = {
    "latitude": 32.72,
    "longitude": -117.16,
    "timezone": "America/Los_Angeles",
    "daily": {
        "time": ["2026-08-27", "2026-08-28", "2026-08-29"],
        "temperature_2m_max": [24.1, 25.6, 23.8],
        "temperature_2m_min": [18.2, 18.9, 17.5],
        "precipitation_sum": [0.0, 0.0, 1.2],
        "precipitation_probability_max": [5, 5, 40],
        "weather_code": [0, 1, 61],
    },
}

# actuals responses don't have precipitation_probability_max
SAMPLE_ACTUALS_RESPONSE = {
    "latitude": 32.72,
    "longitude": -117.16,
    "timezone": "America/Los_Angeles",
    "daily": {
        "time": ["2026-08-20"],
        "temperature_2m_max": [23.9],
        "temperature_2m_min": [17.8],
        "precipitation_sum": [0.0],
        "weather_code": [0],
    },
}


def test_parses_each_day_into_its_own_row():
    rows = parse_daily_response(SAMPLE_FORECAST_RESPONSE)
    assert len(rows) == 3
    assert rows[0]["target_date"] == "2026-08-27"
    assert rows[2]["target_date"] == "2026-08-29"


def test_values_match_the_right_day():
    # catches an off-by-one that'd attach day 1's temp to day 2's row
    rows = parse_daily_response(SAMPLE_FORECAST_RESPONSE)
    assert rows[1]["temperature_2m_max"] == 25.6
    assert rows[2]["precipitation_sum"] == 1.2


def test_extra_fields_get_merged_into_every_row():
    rows = parse_daily_response(
        SAMPLE_FORECAST_RESPONSE,
        extra_fields={"city": "San Diego", "forecast_made_on": "2026-08-27"},
    )
    assert all(r["city"] == "San Diego" for r in rows)
    assert all(r["forecast_made_on"] == "2026-08-27" for r in rows)


def test_missing_field_is_skipped_not_crashed_on():
    rows = parse_daily_response(SAMPLE_ACTUALS_RESPONSE)
    assert "precipitation_probability_max" not in rows[0]
    assert rows[0]["temperature_2m_max"] == 23.9


def test_empty_daily_block_returns_empty_list():
    assert parse_daily_response({"daily": {"time": []}}) == []
