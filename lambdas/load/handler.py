import json
import os

import boto3
import snowflake

from typing import List
from contextlib import contextmanager


def lambda_handler(event, context):
    pass


def get_snowflake_conn():
    secret_id = os.environ["SNOWFLAKE_SECRET_ID"]
    client = boto3.client("secretsmanager")
    secret = client.get_secret_value(SecretId=secret_id)
    secret = json.loads(secret["SecretString"])

    return snowflake.connector.connect(
        account=f"{secret['organization']}-{secret['account']}",
        user=secret["username"],
        password=secret["password"],
        warehouse="TRANSFORM_WH",
        database="REAL_ESTATE",
        schema="STAGING",
    )


@contextmanager
def snowflake_execute(queries: List[str]):
    pass
