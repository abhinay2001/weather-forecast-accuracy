# tests aggregate_previous_runs_to_daily against a fixture shaped like
# the real previous-runs-api hourly response - no network needed

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from open_meteo_client import aggregate_previous_runs_to_daily  # noqa: E402


def _hourly_fixture():
    times = []
    for day in ["2026-08-20", "2026-08-21"]:
        for h in range(24):
            times.append(f"{day}T{h:02d}:00")
    n = len(times)
    return {
        "hourly": {
            "time": times,
            "temperature_2m_previous_day1": [10 + (i % 24) * 5 / 23 for i in range(n)],
            "temperature_2m_previous_day2": [12 + (i % 24) * 5 / 23 for i in range(n)],
            "precipitation_previous_day1": [0.1] * n,
            "precipitation_previous_day2": [0.0] * n,
        }
    }


def test_produces_one_row_per_date_per_lead_time():
    rows = aggregate_previous_runs_to_daily(_hourly_fixture())
    assert len(rows) == 4  # 2 dates x 2 lead times


def test_different_lead_times_keep_separate_values():
    rows = aggregate_previous_runs_to_daily(_hourly_fixture())
    day1_rows = [r for r in rows if r["target_date"] == "2026-08-20"]
    lead1 = next(r for r in day1_rows if r["forecast_made_on"] == "2026-08-19")
    lead2 = next(r for r in day1_rows if r["forecast_made_on"] == "2026-08-18")
    # lead2 uses a different temp series than lead1 - this catches a bug
    # where both leads would accidentally read the same column
    assert lead1["temperature_2m_max"] != lead2["temperature_2m_max"]
    assert lead1["temperature_2m_max"] == 15.0
    assert lead2["temperature_2m_max"] == 17.0


def test_forecast_made_on_is_target_date_minus_lead_days():
    rows = aggregate_previous_runs_to_daily(_hourly_fixture())
    row = next(r for r in rows if r["target_date"] == "2026-08-21" and r["forecast_made_on"] == "2026-08-19")
    # lead 2 for Aug 21 was "made" on Aug 19 (21 - 2 = 19)
    assert row["temperature_2m_max"] == 17.0


def test_precipitation_summed_across_the_day():
    rows = aggregate_previous_runs_to_daily(_hourly_fixture())
    lead1_row = next(r for r in rows if r["target_date"] == "2026-08-20" and r["forecast_made_on"] == "2026-08-19")
    assert lead1_row["precipitation_sum"] == round(0.1 * 24, 2)


def test_missing_lead_time_column_is_skipped():
    payload = {"hourly": {"time": ["2026-08-20T00:00"], "temperature_2m_previous_day1": [10.0]}}
    rows = aggregate_previous_runs_to_daily(payload)
    assert len(rows) == 1  # only day1 present, day2-7 columns absent entirely
