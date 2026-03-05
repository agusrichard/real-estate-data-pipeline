import io
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3
import polars as pl

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")


def lambda_handler(event, context):
    bucket = os.environ["BUCKET_NAME"]
    source_key = os.environ["SOURCE_KEY"]
    execution_date = event.get(
        "execution_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    batch_id = str(uuid.uuid4())
    ingested_at = datetime.now(timezone.utc).isoformat()
    prefix = f"raw/kaggle/{execution_date}/"
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
    if response.get("KeyCount", 0) > 0:
        logger.info(f"Partition already exists | prefix={prefix} - skipping")
        return {"statusCode": 200, "body": {"status": "skipped", "prefix": prefix}}

    logger.info(
        f"Starting ingestion | batch_id={batch_id} "
        f"execution_date={execution_date} source={source_key}"
    )

    response = s3.get_object(Bucket=bucket, Key=source_key)
    csv_buffer = io.BytesIO(response["Body"].read())
    df = pl.read_csv(csv_buffer, infer_schema_length=10_000)
    logger.info(f"CSV loaded | rows={df.shape[0]} columns={df.shape[1]}")

    partitions = df.partition_by("state", maintain_order=False)
    total = len(partitions)
    logger.info(f"Partitioning complete | partitions={total}")

    chunks_written = 0
    for partition in partitions:
        state = partition["state"][0]

        partition = partition.with_columns(
            [
                pl.lit(ingested_at).alias("ingested_at"),
                pl.lit("kaggle").alias("source"),
                pl.lit(batch_id).alias("batch_id"),
            ]
        )

        parquet_buffer = io.BytesIO()
        partition.write_parquet(parquet_buffer)

        output_key = f"raw/kaggle/{execution_date}/{state}.parquet"
        s3.put_object(Bucket=bucket, Key=output_key, Body=parquet_buffer.getvalue())
        chunks_written += 1
        logger.info(
            f"Uploaded partition {chunks_written}/{total} | "
            f"state={state} rows={len(partition)} key={output_key}"
        )

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "kaggle",
        "batch_id": batch_id,
        "execution_date": execution_date,
        "records_count": df.shape[0],
        "chunks_written": chunks_written,
        "status": "success",
    }
    logger.info(json.dumps(summary))

    return {"statusCode": 200, "body": summary}
