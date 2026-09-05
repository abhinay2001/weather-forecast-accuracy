select
    lead_time_days,
    count(*) as forecast_count,
    round(avg(temp_max_abs_error)::numeric, 2) as avg_temp_max_abs_error,
    round(avg(temp_min_abs_error)::numeric, 2) as avg_temp_min_abs_error,
    round(avg((precip_predicted = precip_occurred)::int)::numeric, 2) as precip_hit_rate
from {{ ref('int_forecast_vs_actual') }}
group by lead_time_days
order by lead_time_days
