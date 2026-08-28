# small wrapper around the two open-meteo endpoints we use
# docs: https://open-meteo.com/en/docs - no key needed, free

from datetime import date

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

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


if __name__ == "__main__":
    # manual check - needs real internet, run locally
    sample = get_forecast(32.7157, -117.1611, forecast_days=3)
    for row in parse_daily_response(sample, {"city": "San Diego", "forecast_made_on": str(date.today())}):
        print(row)
