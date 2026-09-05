select
    target_date,
    count(distinct city) as cities_covered,
    round(avg(temp_max_abs_error)::numeric, 2) as avg_temp_max_abs_error,
    round(avg(temp_min_abs_error)::numeric, 2) as avg_temp_min_abs_error
from {{ ref('int_forecast_vs_actual') }}
group by target_date
order by target_date
