import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import boto3
import requests
from constant import STATE_CODES

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
secretsmanager = boto3.client("secretsmanager")

BASE_URL = "https://api.rentcast.io/v1/listings/sale"
PAGE_SIZE = 500
REQUEST_RETRY = 2
REQUEST_TIMEOUT_SECOND = 30
REQUEST_WAIT_SECOND = 30


def get_api_key() -> str:
    secret_id = os.environ["RENTCAST_SECRET_ID"]
    response = secretsmanager.get_secret_value(SecretId=secret_id)
    return json.loads(response["SecretString"])["api_key"]


def fetch_listings(api_key: str, state: str, max_pages: int = 1) -> list[dict]:
    """Fetch active sale listings for a state, handling pagination.

    Args:
        max_pages: Maximum number of pages to fetch. 0 means unlimited (fetch all).
    """
    headers = {"X-Api-Key": api_key}
    all_records: list[dict] = []
    offset = 0
    pages_fetched = 0
    total_count: int | None = None
    state_code = STATE_CODES.get(state)
    if state_code is None:
        raise ValueError(
            f"Unknown state name: '{state}'. Must be a full state name (e.g. 'Texas')."
        )

    while True:
        params = {
            "state": state_code,
            "status": "Active",
            "limit": PAGE_SIZE,
            "offset": offset,
            "includeTotalCount": "true",
        }

        response = _get_with_retry(headers, params, state_code, offset)
        if response is None:
            logger.error(
                f"Skipping remaining pages for state={state} after rate limit failure"
            )
            break

        if total_count is None:
            total_count = int(response.headers.get("x-total-count", 0))
            logger.info(
                f"Total records available | state={state} total_count={total_count}"
            )

        records = response.json()
        all_records.extend(records)
        pages_fetched += 1
        logger.info(
            f"Fetched page | state={state} offset={offset} "
            f"page_size={len(records)} fetched={len(all_records)}/{total_count}"
        )

        if len(records) < PAGE_SIZE:
            break
        if max_pages and pages_fetched >= max_pages:
            logger.info(f"Reached max_pages={max_pages} for state={state}, stopping")
            break

        offset += PAGE_SIZE

    return all_records


def _get_with_retry(
    headers: dict, params: dict, state: str, offset: int
) -> requests.Response | None:
    """Make a GET request, retrying on HTTP 429 or transient network errors."""
    for attempt in range(REQUEST_RETRY):
        try:
            response = requests.get(
                BASE_URL, headers=headers, params=params, timeout=REQUEST_TIMEOUT_SECOND
            )

            if response.status_code == 429:
                if attempt < REQUEST_RETRY - 1:
                    logger.warning(
                        f"Rate limited | state={state} offset={offset}"
                        f" — retrying in {REQUEST_WAIT_SECOND}s"
                    )
                    time.sleep(REQUEST_WAIT_SECOND)
                    continue
                logger.error(
                    f"Rate limited on final attempt | state={state}"
                    f" offset={offset} — skipping"
                )
                return None

            response.raise_for_status()
            return response

        except requests.exceptions.Timeout:
            logger.warning(
                f"Request timed out | state={state} offset={offset}"
                f" attempt={attempt + 1}"
            )
        except requests.exceptions.ConnectionError:
            logger.warning(
                f"Connection error | state={state} offset={offset}"
                f" attempt={attempt + 1}"
            )
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error | state={state} offset={offset}"
                f" status={e.response.status_code}"
            )
            return None

        if attempt < REQUEST_RETRY - 1:
            time.sleep(REQUEST_WAIT_SECOND)

    logger.error(f"All {REQUEST_RETRY} attempts failed | state={state} offset={offset}")
    return None


def lambda_handler(event: dict, context) -> dict:
    bucket = os.environ["BUCKET_NAME"]
    default_states = os.environ.get("TARGET_STATES", "")

    execution_date = event.get(
        "execution_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    states = event.get("states") or [
        s.strip() for s in default_states.split(",") if s.strip()
    ]

    if not states:
        raise ValueError(
            "No states configured. Set TARGET_STATES env var"
            " or pass 'states' in the event payload."
        )

    batch_id = str(uuid.uuid4())
    ingested_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"Starting RentCast ingestion | batch_id={batch_id} "
        f"execution_date={execution_date} states={states}"
    )

    max_pages = event.get("max_pages", 1)
    api_key = get_api_key()
    results = []

    for state in states:
        output_key = f"raw/rentcast/{execution_date}/listings-sale/{state}.json"

        try:
            s3.head_object(Bucket=bucket, Key=output_key)
            logger.info(
                f"File already exists | key={output_key} - skipping state={state}"
            )
            continue
        except s3.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "404":
                raise

        logger.info(f"Processing state={state}")
        records = fetch_listings(api_key, state, max_pages=max_pages)

        payload = {
            "batch_id": batch_id,
            "ingested_at": ingested_at,
            "source": "rentcast",
            "endpoint": "listings/sale",
            "state": state,
            "execution_date": execution_date,
            "record_count": len(records),
            "records": records,
        }

        s3.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
        )

        logger.info(f"Uploaded | state={state} records={len(records)} key={output_key}")
        results.append(
            {"state": state, "record_count": len(records), "s3_key": output_key}
        )

    summary = {
        "batch_id": batch_id,
        "execution_date": execution_date,
        "ingested_at": ingested_at,
        "states_processed": len(results),
        "records_count": sum(r["record_count"] for r in results),
    }

    logger.info(json.dumps(summary))

    return {"statusCode": 200, "body": summary}
