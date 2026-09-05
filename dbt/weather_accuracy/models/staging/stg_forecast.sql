select
    city,
    state,
    forecast_made_on,
    target_date,
    target_date - forecast_made_on as lead_time_days,
    temperature_2m_max as predicted_temp_max,
    temperature_2m_min as predicted_temp_min,
    precipitation_sum as predicted_precipitation,
    precipitation_probability_max,
    weather_code as predicted_weather_code
from {{ source('raw', 'forecast_daily') }}
