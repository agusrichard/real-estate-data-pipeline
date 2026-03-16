import json
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


def create_lambda_operator(
    task_id: str, extra_payload: dict | None = None
) -> LambdaInvokeFunctionOperator:
    base = {"execution_date": "{{ ds }}"}
    base.update(extra_payload or {})
    return LambdaInvokeFunctionOperator(
        task_id=task_id,
        function_name=snake_to_kebab(task_id),
        payload=json.dumps(base),
    )


def check_data_quality(**context):
    load_response = context["ti"].xcom_pull(task_ids="load")
    response = json.loads(load_response)
    body = response["body"]

    quality_checks = body["quality_checks_result"]
    failed = [check for check in quality_checks if not check["passed"]]

    if failed:
        for check in failed:
            logger.error(f"FAILED: {check['name']} (value: {check['value']})")
        raise ValueError(
            f"{len(failed)} quality check(s) failed: {[c['name'] for c in failed]}"
        )

    logger.info(f"All {len(quality_checks)} quality checks passed")
    logger.info(f"Batch: {body['batch_id']}")
    logger.info(f"Rows loaded: {body['rows_loaded']}")


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
    ingest_rentcast = LambdaInvokeFunctionOperator(
        task_id="ingest_rentcast",
        function_name="ingest-rentcast",
        payload=(
            '{"execution_date": "{{ ds }}",'
            ' "states": {{ dag_run.conf.get("states", ["Alabama"]) | tojson }}}'
        ),
    )
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
