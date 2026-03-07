import io
from unittest.mock import patch

import polars as pl
import pytest
from botocore.exceptions import ClientError

from conftest import load_module

handler = load_module("lambdas/ingest_kaggle/handler.py", "kaggle_handler")


@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    monkeypatch.setenv("BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("SOURCE_KEY", "raw/kaggle/source/realtor-data.csv")


def make_csv_bytes() -> bytes:
    """Minimal two-state CSV that the handler can partition."""
    df = pl.DataFrame(
        {
            "state": ["California", "Texas", "California"],
            "price": [500_000, 300_000, 600_000],
        }
    )
    buf = io.BytesIO()
    df.write_csv(buf)
    return buf.getvalue()


@patch("kaggle_handler.s3")
def test_idempotency_skip(mock_s3):
    mock_s3.list_objects_v2.return_value = {"KeyCount": 1}

    result = handler.lambda_handler({"execution_date": "2024-01-01"}, {})

    assert result["statusCode"] == 200
    assert result["body"]["status"] == "skipped"
    mock_s3.get_object.assert_not_called()


@patch("kaggle_handler.s3")
def test_s3_read_failure(mock_s3):
    mock_s3.list_objects_v2.return_value = {"KeyCount": 0}
    mock_s3.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}}, "GetObject"
    )

    with pytest.raises(ClientError):
        handler.lambda_handler({"execution_date": "2024-01-01"}, {})


@patch("kaggle_handler.s3")
def test_happy_path(mock_s3):
    mock_s3.list_objects_v2.return_value = {"KeyCount": 0}
    mock_s3.get_object.return_value = {"Body": io.BytesIO(make_csv_bytes())}

    result = handler.lambda_handler({"execution_date": "2024-01-01"}, {})

    assert result["statusCode"] == 200
    # CSV has two distinct states: California and Texas
    assert mock_s3.put_object.call_count == 2


@patch("kaggle_handler.s3")
def test_metadata_columns_present(mock_s3):
    mock_s3.list_objects_v2.return_value = {"KeyCount": 0}
    mock_s3.get_object.return_value = {"Body": io.BytesIO(make_csv_bytes())}

    captured: list[bytes] = []
    mock_s3.put_object.side_effect = lambda **kwargs: captured.append(kwargs["Body"])

    handler.lambda_handler({"execution_date": "2024-01-01"}, {})

    assert len(captured) > 0
    df = pl.read_parquet(io.BytesIO(captured[0]))
    assert "ingested_at" in df.columns
    assert "source" in df.columns
    assert "batch_id" in df.columns
