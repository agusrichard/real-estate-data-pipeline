import importlib.util
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

# constant.py lives alongside handler.py — add the directory to sys.path so
# the handler's "from constant import STATE_CODES" resolves correctly.
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "../lambdas/ingest_rentcast")
)

_handler_path = os.path.join(
    os.path.dirname(__file__), "../lambdas/ingest_rentcast/handler.py"
)
_spec = importlib.util.spec_from_file_location("rentcast_handler", _handler_path)
handler = importlib.util.module_from_spec(_spec)
sys.modules["rentcast_handler"] = handler
_spec.loader.exec_module(handler)


@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    monkeypatch.setenv("BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("RENTCAST_SECRET_ID", "rentcast/api-key")
    monkeypatch.setenv("TARGET_STATES", "")


def make_api_response(records: list, total_count: int | None = None) -> MagicMock:
    """Build a mock requests.Response for a successful RentCast API call."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = records
    resp.headers.get.return_value = str(
        total_count if total_count is not None else len(records)
    )
    return resp


# ---------------------------------------------------------------------------
# fetch_listings tests
# ---------------------------------------------------------------------------


@patch("rentcast_handler.requests.get")
def test_fetch_single_page(mock_get):
    records = [{"id": i} for i in range(5)]
    mock_get.return_value = make_api_response(records)

    result = handler.fetch_listings("api-key", "Texas")

    assert mock_get.call_count == 1
    assert result == records


@patch("rentcast_handler.requests.get")
def test_fetch_pagination(mock_get):
    page1 = [{"id": i} for i in range(handler.PAGE_SIZE)]
    page2 = [{"id": i} for i in range(3)]
    total = handler.PAGE_SIZE + 3
    mock_get.side_effect = [
        make_api_response(page1, total),
        make_api_response(page2, total),
    ]

    # max_pages=0 means unlimited — fetches until a partial page is returned
    result = handler.fetch_listings("api-key", "Texas", max_pages=0)

    assert mock_get.call_count == 2
    assert len(result) == total


@patch("rentcast_handler.time.sleep")
@patch("rentcast_handler.requests.get")
def test_rate_limit_retry(mock_get, mock_sleep):
    rate_limited = MagicMock()
    rate_limited.status_code = 429
    success = make_api_response([{"id": 1}])
    mock_get.side_effect = [rate_limited, success]

    result = handler.fetch_listings("api-key", "Texas")

    assert mock_get.call_count == 2
    assert result == [{"id": 1}]
    mock_sleep.assert_called_once()


@patch("rentcast_handler.time.sleep")
@patch("rentcast_handler.requests.get")
def test_rate_limit_exhausted(mock_get, mock_sleep):
    rate_limited = MagicMock()
    rate_limited.status_code = 429
    mock_get.return_value = rate_limited

    result = handler.fetch_listings("api-key", "Texas")

    assert result == []


# ---------------------------------------------------------------------------
# lambda_handler tests
# ---------------------------------------------------------------------------


def test_missing_states_raises():
    # TARGET_STATES is "" (from fixture) and event has no "states" key
    with pytest.raises(ValueError):
        handler.lambda_handler({"execution_date": "2024-01-01"}, {})


@patch("rentcast_handler.requests.get")
@patch("rentcast_handler.secretsmanager")
@patch("rentcast_handler.s3")
def test_idempotency_skip_state(mock_s3, mock_secretsmanager, mock_get):
    mock_secretsmanager.get_secret_value.return_value = {
        "SecretString": json.dumps({"api_key": "test-key"})
    }
    # head_object returning without raising means the file already exists
    mock_s3.head_object.return_value = {}

    result = handler.lambda_handler(
        {"execution_date": "2024-01-01", "states": ["Texas"]}, {}
    )

    assert result["statusCode"] == 200
    mock_get.assert_not_called()


@patch("rentcast_handler.requests.get")
@patch("rentcast_handler.secretsmanager")
@patch("rentcast_handler.s3")
def test_happy_path(mock_s3, mock_secretsmanager, mock_get):
    mock_secretsmanager.get_secret_value.return_value = {
        "SecretString": json.dumps({"api_key": "test-key"})
    }
    # Make s3.exceptions.ClientError a real exception class so the except
    # clause in the handler can catch the ClientError we raise below
    mock_s3.exceptions.ClientError = ClientError
    mock_s3.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
    )
    mock_get.return_value = make_api_response([{"id": 1}, {"id": 2}])

    result = handler.lambda_handler(
        {"execution_date": "2024-01-01", "states": ["Texas", "Florida"]}, {}
    )

    assert result["statusCode"] == 200
    assert result["body"]["states_processed"] == 2
    assert mock_s3.put_object.call_count == 2
