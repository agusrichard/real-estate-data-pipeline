import io       
import os
import uuid
from datetime import datetime, timezone

import boto3
import polars as pl

s3 = boto3.client("s3")

def lambda_handler(event, context):
	bucket = os.environ["BUCKET_NAME"]
	source_key = os.environ["SOURCE_KEY"]
	execution_date = event.get("execution_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
	batch_id = str(uuid.uuid4())
	ingested_at = datetime.now(timezone.utc).isoformat()

	response = s3.get_object(Bucket=bucket, Key=source_key)
	csv_buffer = io.BytesIO(response["Body"].read())
	df = pl.read_csv(csv_buffer, infer_schema_length=10_000)
	partitions = df.partition_by("state", maintain_order=False)

	chunks_written = 0
	for partition in partitions:
		state = partition["state"][0]

		partition = partition.with_columns([
			pl.lit(ingested_at).alias("ingested_at"),
			pl.lit("kaggle").alias("source"),
			pl.lit(batch_id).alias("batch_id"),
		])

		parquet_buffer = io.BytesIO()
		partition.write_parquet(parquet_buffer)

		output_key = f"raw/kaggle/{execution_date}/{state}.parquet"
		s3.put_object(Bucket=bucket, Key=output_key,
	Body=parquet_buffer.getvalue())
		chunks_written += 1

	return {
		"statusCode": 200,
		"body": {
			"batch_id": batch_id,
			"chunks_written": chunks_written,
			"ingested_at": ingested_at,
			"execution_date": execution_date,
		}
	}