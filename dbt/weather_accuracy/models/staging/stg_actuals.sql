select
    city,
    state,
    target_date,
    temperature_2m_max as actual_temp_max,
    temperature_2m_min as actual_temp_min,
    precipitation_sum as actual_precipitation,
    weather_code as actual_weather_code
from {{ source('raw', 'actuals_daily') }}
