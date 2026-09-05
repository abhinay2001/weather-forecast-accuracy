select
    f.city,
    f.state,
    f.forecast_made_on,
    f.target_date,
    f.lead_time_days,
    f.predicted_temp_max,
    f.predicted_temp_min,
    f.predicted_precipitation,
    a.actual_temp_max,
    a.actual_temp_min,
    a.actual_precipitation,
    round((f.predicted_temp_max - a.actual_temp_max)::numeric, 2) as temp_max_error,
    round((f.predicted_temp_min - a.actual_temp_min)::numeric, 2) as temp_min_error,
    round(abs(f.predicted_temp_max - a.actual_temp_max)::numeric, 2) as temp_max_abs_error,
    round(abs(f.predicted_temp_min - a.actual_temp_min)::numeric, 2) as temp_min_abs_error,
    (f.predicted_precipitation > 0) as precip_predicted,
    (a.actual_precipitation > 0) as precip_occurred
from {{ ref('stg_forecast') }} f
inner join {{ ref('stg_actuals') }} a
    on f.city = a.city and f.target_date = a.target_date
