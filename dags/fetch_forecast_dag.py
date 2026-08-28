# daily DAG - pulls today's 7-day forecast for all cities
#
# catchup is off on purpose. "today's forecast" only makes sense on the
# day it was fetched, there's no way to ask open-meteo what it would
# have forecast 3 days ago. actuals (ground truth) come from a
# different DAG that hits the historical endpoint instead.

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def _run_fetch_forecast():
    import fetch_forecast
    fetch_forecast.main()


default_args = {
    "owner": "abhinay",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="fetch_forecast_daily",
    description="fetch today's 7-day forecast for all tracked cities",
    default_args=default_args,
    schedule_interval="0 13 * * *",  # 13:00 UTC ~ 6am pacific
    start_date=datetime(2026, 8, 1),
    catchup=False,
    max_active_runs=1,
    tags=["weather", "extract"],
) as dag:
    fetch_forecast_task = PythonOperator(
        task_id="fetch_forecast",
        python_callable=_run_fetch_forecast,
    )
