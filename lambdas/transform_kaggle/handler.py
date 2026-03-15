import io
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3
import polars as pl
from kaggle import transform

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

    raw_prefix = f"raw/kaggle/{execution_date}/"
    staging_prefix = f"staging/kaggle/{execution_date}/"

    # Read all raw Parquet files for this partition
    logger.info(f"Reading raw data | prefix={raw_prefix}")
    response = s3.list_objects_v2(Bucket=bucket, Prefix=raw_prefix)
    keys = [obj["Key"] for obj in response.get("Contents", [])]

    tmp_dir = "/tmp/raw_kaggle"
    os.makedirs(tmp_dir, exist_ok=True)
    for i, key in enumerate(keys):
        obj = s3.get_object(Bucket=bucket, Key=key)
        with open(f"{tmp_dir}/{i}.parquet", "wb") as f:
            f.write(obj["Body"].read())
    logger.info(f"Downloaded {len(keys)} files to {tmp_dir} | ready for lazy scan")

    lf = pl.scan_parquet(f"{tmp_dir}/*.parquet")

    dim_location, dim_property_type, fact_listings = transform(
        lf, batch_id, ingested_at
    )

    # Write output tables to staging
    for name, frame in [
        ("dim_location", dim_location),
        ("dim_property_type", dim_property_type),
        ("fact_listings", fact_listings),
    ]:
        buf = io.BytesIO()
        frame.write_parquet(buf)
        buf.seek(0)
        key = f"{staging_prefix}{name}.parquet"
        s3.put_object(Bucket=bucket, Key=key, Body=buf)
        logger.info(f"Uploaded {name} | rows={frame.shape[0]} key={key}")

    summary = {
        "status": "success",
        "source": "kaggle",
        "batch_id": batch_id,
        "execution_date": execution_date,
        "fact_listings_rows": fact_listings.shape[0],
        "dim_location_rows": dim_location.shape[0],
    }
    logger.info(json.dumps(summary))
    return {"statusCode": 200, "body": summary}
