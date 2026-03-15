import json
import sys
from unittest.mock import MagicMock, call, patch

import pytest

from conftest import load_module

# snowflake-connector-python is not installed in the test venv,
# so we stub the import before loading the handler module.
snowflake_mock = MagicMock()
sys.modules["snowflake"] = snowflake_mock
sys.modules["snowflake.connector"] = snowflake_mock.connector

handler = load_module("lambdas/load/handler.py", "load_handler")

FAKE_SECRET = {
    "organization": "my_org",
    "account": "my_account",
    "username": "user",
    "password": "pass",
}


@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_SECRET_ID", "test/snowflake-secret")


@pytest.fixture()
def mock_cursor():
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    return cursor


@pytest.fixture()
def mock_connection(mock_cursor):
    conn = MagicMock()
    conn.cursor.return_value = mock_cursor
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn


# ── get_snowflake_conn ──────────────────────────────────────────────


@patch("load_handler.snowflake.connector.connect")
@patch("load_handler.boto3.client")
def test_get_snowflake_conn(mock_boto_client, mock_sf_connect):
    sm = MagicMock()
    sm.get_secret_value.return_value = {
        "SecretString": json.dumps(FAKE_SECRET),
    }
    mock_boto_client.return_value = sm

    handler.get_snowflake_conn()

    sm.get_secret_value.assert_called_once_with(SecretId="test/snowflake-secret")
    mock_sf_connect.assert_called_once_with(
        account="my_org-my_account",
        user="user",
        role="PIPELINE_ROLE",
        password="pass",
        warehouse="TRANSFORM_WH",
        database="REAL_ESTATE",
        schema="STAGING",
    )


# ── snowflake_execute ───────────────────────────────────────────────


def test_snowflake_execute(mock_connection, mock_cursor):
    queries = ["SELECT 1", "SELECT 2", "SELECT 3"]

    handler.snowflake_execute(mock_connection, queries)

    assert mock_cursor.execute.call_args_list == [
        call("SELECT 1"),
        call("SELECT 2"),
        call("SELECT 3"),
    ]


# ── truncate_staging ────────────────────────────────────────────────


def test_truncate_staging(mock_connection, mock_cursor):
    handler.truncate_staging(mock_connection)

    executed = [c.args[0] for c in mock_cursor.execute.call_args_list]
    assert len(executed) == 5
    for q in executed:
        assert q.startswith("TRUNCATE TABLE REAL_ESTATE.STAGING.stg_")


# ── load_to_staging ─────────────────────────────────────────────────


def test_load_to_staging(mock_connection, mock_cursor):
    handler.load_to_staging(mock_connection, "2024-06-01")

    executed = [c.args[0] for c in mock_cursor.execute.call_args_list]
    assert len(executed) == 5
    for q in executed:
        assert "COPY INTO" in q
        assert "FILE_FORMAT = (TYPE = PARQUET)" in q

    kaggle_queries = [q for q in executed if "kaggle/2024-06-01" in q]
    rentcast_queries = [q for q in executed if "rentcast/2024-06-01" in q]
    assert len(kaggle_queries) == 2
    assert len(rentcast_queries) == 3


# ── merge_dim_location ──────────────────────────────────────────────


def test_merge_dim_location(mock_connection, mock_cursor):
    handler.merge_dim_location(mock_connection)

    executed = [c.args[0] for c in mock_cursor.execute.call_args_list]
    assert len(executed) == 1
    assert "MERGE INTO REAL_ESTATE.ANALYTICS.dim_location" in executed[0]
    assert "REAL_ESTATE.STAGING.stg_dim_location" in executed[0]


# ── insert_fact_tables ──────────────────────────────────────────────


def test_insert_fact_tables(mock_connection, mock_cursor):
    handler.insert_fact_tables(mock_connection)

    executed = [c.args[0] for c in mock_cursor.execute.call_args_list]
    assert len(executed) == 3

    for q in executed:
        assert "INSERT INTO REAL_ESTATE.ANALYTICS." in q
        assert "JOIN REAL_ESTATE.STAGING.stg_dim_location stg_loc" in q
        assert "JOIN REAL_ESTATE.ANALYTICS.dim_location dim_loc" in q


def test_insert_fact_tables_has_dedup_guard(mock_connection, mock_cursor):
    handler.insert_fact_tables(mock_connection)

    executed = [c.args[0] for c in mock_cursor.execute.call_args_list]
    for q in executed:
        assert "WHERE NOT EXISTS" in q
        assert "existing.batch_id = stg.batch_id" in q


# ── lambda_handler ──────────────────────────────────────────────────


@patch("load_handler.get_snowflake_conn")
def test_lambda_handler_happy_path(mock_get_conn, mock_connection, mock_cursor):
    mock_get_conn.return_value = mock_connection

    result = handler.lambda_handler({"execution_date": "2024-06-01"}, {})

    assert result["statusCode"] == 200
    assert result["body"]["execution_date"] == "2024-06-01"
    assert "ingested_at" in result["body"]

    executed = [c.args[0] for c in mock_cursor.execute.call_args_list]
    truncates = [q for q in executed if "TRUNCATE" in q]
    copies = [q for q in executed if "COPY INTO" in q]
    merges = [q for q in executed if "MERGE INTO" in q]
    inserts = [q for q in executed if "INSERT INTO" in q]
    assert len(truncates) == 5
    assert len(copies) == 5
    assert len(merges) == 1
    assert len(inserts) == 3


@patch("load_handler.get_snowflake_conn")
def test_lambda_handler_default_date(mock_get_conn, mock_connection, mock_cursor):
    mock_get_conn.return_value = mock_connection

    result = handler.lambda_handler({}, {})

    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert result["body"]["execution_date"] == today
