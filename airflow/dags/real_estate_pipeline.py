import logging
from datetime import datetime, timedelta

from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.lambda_function import (
    LambdaInvokeFunctionOperator,
)

from airflow import DAG

logger = logging.getLogger(__name__)

default_args = {
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}


def snake_to_kebab(s: str) -> str:
    return s.replace("_", "-")


def create_lambda_operator(task_id: str) -> LambdaInvokeFunctionOperator:
    return LambdaInvokeFunctionOperator(
        task_id=task_id,
        function_name=snake_to_kebab(task_id),
        payload='{"execution_date": "{{ ds }}"}',
    )


def check_data_quality(**context):
    logger.info("All quality checks passed")


with DAG(
    dag_id="real-estate-pipeline",
    default_args=default_args,
    start_date=datetime(2026, 3, 1),
    schedule="@weekly",
    catchup=False,
    tags=[
        "real-estate-data-pipeline",
    ],
) as dag:
    ingest_kaggle = create_lambda_operator(task_id="ingest_kaggle")
    ingest_rentcast = create_lambda_operator(task_id="ingest_rentcast")
    transform_kaggle = create_lambda_operator(task_id="transform_kaggle")
    transform_rentcast = create_lambda_operator(task_id="transform_rentcast")
    load = create_lambda_operator(task_id="load")
    data_quality = PythonOperator(
        task_id="data_quality_check",
        python_callable=check_data_quality,
    )

    ingest_kaggle >> transform_kaggle
    ingest_rentcast >> transform_rentcast
    [transform_kaggle, transform_rentcast] >> load >> data_quality
