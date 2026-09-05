# small wrapper around the two open-meteo endpoints we use
# docs: https://open-meteo.com/en/docs - no key needed, free

from datetime import date, timedelta

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
LEAD_DAYS = range(1, 8)

# same var names for forecast + actuals so the two tables line up later
DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",  # only exists on forecast, not actuals
    "weather_code",
]

TIMEOUT = 15


def _get(url, params):
    resp = requests.get(url, params=params, timeout=TIMEOUT)
    data = resp.json()

    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(data.get("reason"))

    resp.raise_for_status()
    return data


def get_forecast(latitude, longitude, forecast_days=7):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join(DAILY_VARS),
        "forecast_days": forecast_days,
        "timezone": "auto",
    }
    return _get(FORECAST_URL, params)


def get_actuals(latitude, longitude, start_date, end_date=None):
    # ERA5 reanalysis has a ~5-7 day lag, so don't ask for yesterday,
    # you'll just get nulls back
    end_date = end_date or start_date
    daily_vars = [v for v in DAILY_VARS if v != "precipitation_probability_max"]
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(daily_vars),
        "timezone": "auto",
    }
    return _get(ARCHIVE_URL, params)


def parse_daily_response(payload, extra_fields=None):
    daily = payload.get("daily", {})
    dates = daily.get("time", [])
    rows = []
    for i, day in enumerate(dates):
        row = {"target_date": day}
        for var in DAILY_VARS:
            if var in daily:
                row[var] = daily[var][i]
        if extra_fields:
            row.update(extra_fields)
        rows.append(row)
    return rows


def get_previous_runs(latitude, longitude, past_days=90):
    # hourly-only endpoint - temperature_2m_previous_day1..7 gives the
    # value forecast N days before the actual hour. we aggregate these
    # to daily max/min ourselves below, same for precipitation.
    temp_vars = [f"temperature_2m_previous_day{d}" for d in LEAD_DAYS]
    precip_vars = [f"precipitation_previous_day{d}" for d in LEAD_DAYS]
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(temp_vars + precip_vars),
        "past_days": past_days,
        "forecast_days": 1,
        "timezone": "auto",
    }
    return _get(PREVIOUS_RUNS_URL, params)


def aggregate_previous_runs_to_daily(payload, extra_fields=None):
    # turns the hourly previous_dayN columns into one row per
    # (target_date, lead_time) with daily max/min/sum, in the same
    # shape as raw.forecast_daily - so it can reuse the same upsert
    # as the live daily forecast fetch
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    rows = []

    for lead in LEAD_DAYS:
        temps = hourly.get(f"temperature_2m_previous_day{lead}")
        precs = hourly.get(f"precipitation_previous_day{lead}")
        if not temps:
            continue

        by_date = {}
        for i, ts in enumerate(times):
            day = ts[:10]
            if day not in by_date:
                by_date[day] = {"temps": [], "precip_sum": 0.0, "has_precip": False}
            t = temps[i] if i < len(temps) else None
            if t is not None:
                by_date[day]["temps"].append(t)
            if precs is not None and i < len(precs) and precs[i] is not None:
                by_date[day]["precip_sum"] += precs[i]
                by_date[day]["has_precip"] = True

        for target_date, agg in by_date.items():
            if not agg["temps"]:
                continue  # this lead time isn't resolved for this date yet
            forecast_made_on = str(date.fromisoformat(target_date) - timedelta(days=lead))
            row = {
                "target_date": target_date,
                "forecast_made_on": forecast_made_on,
                "temperature_2m_max": max(agg["temps"]),
                "temperature_2m_min": min(agg["temps"]),
                "precipitation_sum": round(agg["precip_sum"], 2) if agg["has_precip"] else None,
                "precipitation_probability_max": None,
                "weather_code": None,
            }
            if extra_fields:
                row.update(extra_fields)
            rows.append(row)

    return rows


if __name__ == "__main__":
    # manual check - needs real internet, run locally
    sample = get_forecast(32.7157, -117.1611, forecast_days=3)
    for row in parse_daily_response(sample, {"city": "San Diego", "forecast_made_on": str(date.today())}):
        print(row)
