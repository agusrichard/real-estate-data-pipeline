import io
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3
from rentcast import transform

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")


def lambda_handler(event, context):
    bucket = os.environ["BUCKET_NAME"]
    execution_date = event.get(
        "execution_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    batch_id = str(uuid.uuid4())
    ingested_at = datetime.now(timezone.utc).isoformat()

    listings_prefix = f"raw/rentcast/{execution_date}/listings-sale/"
    market_prefix = f"raw/rentcast/{execution_date}/market/"
    staging_prefix = f"staging/rentcast/{execution_date}/"

    # Read all listings JSON files and combine records
    logger.info(f"Reading listings | prefix={listings_prefix}")
    response = s3.list_objects_v2(Bucket=bucket, Prefix=listings_prefix)
    listing_keys = [obj["Key"] for obj in response.get("Contents", [])]

    records = []
    for key in listing_keys:
        obj = s3.get_object(Bucket=bucket, Key=key)
        payload = json.loads(obj["Body"].read())
        records.extend(payload["records"])
    logger.info(
        f"Loaded {len(listing_keys)} listing files | total records={len(records)}"
    )

    # Read market JSON files if present (optional — no market ingest yet)
    logger.info(f"Reading market data | prefix={market_prefix}")
    response = s3.list_objects_v2(Bucket=bucket, Prefix=market_prefix)
    market_keys = [obj["Key"] for obj in response.get("Contents", [])]

    market_raws = []
    for key in market_keys:
        obj = s3.get_object(Bucket=bucket, Key=key)
        market_raws.append(json.loads(obj["Body"].read()))
    logger.info(f"Loaded {len(market_keys)} market files")

    dim_location, dim_property_type, fact_listings, fact_market_stats = transform(
        records, market_raws, batch_id, ingested_at
    )

    # Write output tables to staging
    for name, frame in [
        ("dim_location", dim_location),
        ("dim_property_type", dim_property_type),
        ("fact_listings", fact_listings),
        ("fact_market_stats", fact_market_stats),
    ]:
        buf = io.BytesIO()
        frame.write_parquet(buf)
        key = f"{staging_prefix}{name}.parquet"
        s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
        logger.info(f"Uploaded {name} | rows={frame.shape[0]} key={key}")

    summary = {
        "status": "success",
        "source": "rentcast",
        "batch_id": batch_id,
        "execution_date": execution_date,
        "fact_listings_rows": fact_listings.shape[0],
        "fact_market_stats_rows": fact_market_stats.shape[0],
        "dim_location_rows": dim_location.shape[0],
    }
    logger.info(json.dumps(summary))
    return {"statusCode": 200, "body": summary}
