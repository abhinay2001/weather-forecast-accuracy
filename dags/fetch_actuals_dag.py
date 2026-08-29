# daily DAG - re-sweeps a trailing 14-day window (ending 7 days back,
# to clear ERA5's processing lag) of actual observed weather.
#
# re-sweeping instead of just grabbing "yesterday" means any date that
# was still unresolved on a previous run gets picked up automatically
# once ERA5 catches up, no manual tracking needed.

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def _run_fetch_actuals():
    import fetch_actuals
    fetch_actuals.main()


default_args = {
    "owner": "abhinay",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="fetch_actuals_daily",
    description="sweep the trailing window of actual (ERA5) weather for all tracked cities",
    default_args=default_args,
    schedule_interval="0 14 * * *",  # after the forecast DAG, 14:00 UTC
    start_date=datetime(2026, 8, 1),
    catchup=False,
    max_active_runs=1,
    tags=["weather", "extract"],
) as dag:
    fetch_actuals_task = PythonOperator(
        task_id="fetch_actuals",
        python_callable=_run_fetch_actuals,
    )
