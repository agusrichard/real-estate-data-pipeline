import json
import logging
import os
from datetime import datetime, timezone

import boto3
import snowflake.connector

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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


def snowflake_execute(connection, queries: list[str]):
    with connection.cursor() as cursor:
        for query in queries:
            cursor.execute(query)


def truncate_staging(connection):
    queries = [
        "TRUNCATE TABLE REAL_ESTATE.STAGING.stg_dim_location",
        "TRUNCATE TABLE REAL_ESTATE.STAGING.stg_dim_property_type",
        "TRUNCATE TABLE REAL_ESTATE.STAGING.stg_fact_listings_kaggle",
        "TRUNCATE TABLE REAL_ESTATE.STAGING.stg_fact_listings_rentcast",
        "TRUNCATE TABLE REAL_ESTATE.STAGING.stg_fact_market_stats",
    ]
    snowflake_execute(connection, queries)


def load_to_staging(connection, execution_date: str):
    kaggle = f"@REAL_ESTATE.STAGING.S3_STAGE/kaggle/{execution_date}"
    rentcast = f"@REAL_ESTATE.STAGING.S3_STAGE/rentcast/{execution_date}"
    queries = [
        f"""
        COPY INTO REAL_ESTATE.STAGING.stg_dim_location
        FROM {kaggle}/dim_location.parquet
        FILE_FORMAT = (TYPE = PARQUET) MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;
        """,
        f"""
        COPY INTO REAL_ESTATE.STAGING.stg_fact_listings_kaggle
        FROM {kaggle}/fact_listings.parquet
        FILE_FORMAT = (TYPE = PARQUET) MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;
        """,
        f"""
        COPY INTO REAL_ESTATE.STAGING.stg_dim_location
        FROM {rentcast}/dim_location.parquet
        FILE_FORMAT = (TYPE = PARQUET) MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;
        """,
        f"""
        COPY INTO REAL_ESTATE.STAGING.stg_fact_listings_rentcast
        FROM {rentcast}/fact_listings.parquet
        FILE_FORMAT = (TYPE = PARQUET) MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;
        """,
        f"""
        COPY INTO REAL_ESTATE.STAGING.stg_fact_market_stats
        FROM {rentcast}/fact_market_stats.parquet
        FILE_FORMAT = (TYPE = PARQUET) MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;
        """,
    ]

    snowflake_execute(connection, queries)


def merge_dim_location(connection):
    queries = [
        """
        MERGE INTO REAL_ESTATE.ANALYTICS.dim_location AS target
        USING REAL_ESTATE.STAGING.stg_dim_location AS source
            ON  target.city     = source.city
            AND target.state    = source.state
            AND target.zip_code = source.zip_code
        WHEN NOT MATCHED THEN
            INSERT (location_id, city, state, zip_code)
            VALUES (
                REAL_ESTATE.ANALYTICS.dim_location_seq.NEXTVAL,
                source.city, source.state, source.zip_code
            );
        """
    ]

    snowflake_execute(connection, queries)


def insert_fact_tables(connection):
    queries = [
        """
        INSERT INTO REAL_ESTATE.ANALYTICS.fact_listings
            (location_id, property_type_id, price, status,
             bed, bath, acre_lot, house_size, prev_sold_date, brokered_by,
             source, batch_id, ingested_at)
        SELECT
            dim_loc.location_id,
            stg.property_type_id,
            stg.price, stg.status,
            stg.bed, stg.bath, stg.acre_lot, stg.house_size,
            stg.prev_sold_date, stg.brokered_by,
            stg.source, stg.batch_id, stg.ingested_at
        FROM REAL_ESTATE.STAGING.stg_fact_listings_kaggle stg
        JOIN REAL_ESTATE.ANALYTICS.dim_location dim_loc
            ON  stg.city     = dim_loc.city
            AND stg.state    = dim_loc.state
            AND stg.zip_code = dim_loc.zip_code
        WHERE NOT EXISTS (
            SELECT 1 FROM REAL_ESTATE.ANALYTICS.fact_listings existing
            WHERE existing.batch_id = stg.batch_id
        );
        """,
        """
        INSERT INTO REAL_ESTATE.ANALYTICS.fact_listings
            (location_id, property_type_id, price, status,
             rentcast_id, address, bedrooms, bathrooms,
             square_footage, lot_size, latitude, longitude,
             days_on_market, listed_date,
             source, batch_id, ingested_at)
        SELECT
            dim_loc.location_id,
            stg.property_type_id,
            stg.price, stg.status,
            stg.rentcast_id, stg.address,
            stg.bedrooms, stg.bathrooms,
            stg.square_footage, stg.lot_size,
            stg.latitude, stg.longitude,
            stg.days_on_market, stg.listed_date,
            stg.source, stg.batch_id, stg.ingested_at
        FROM REAL_ESTATE.STAGING.stg_fact_listings_rentcast stg
        JOIN REAL_ESTATE.ANALYTICS.dim_location dim_loc
            ON  stg.city     = dim_loc.city
            AND stg.state    = dim_loc.state
            AND stg.zip_code = dim_loc.zip_code
        WHERE NOT EXISTS (
            SELECT 1 FROM REAL_ESTATE.ANALYTICS.fact_listings existing
            WHERE existing.batch_id = stg.batch_id
        );
        """,
        """
        INSERT INTO REAL_ESTATE.ANALYTICS.fact_market_stats
            (location_id, snapshot_date,
             median_listing_price, median_price_per_sqft, median_days_on_market,
             total_listings, new_listings,
             source, batch_id, ingested_at)
        SELECT
            dim_loc.location_id,
            stg.snapshot_date,
            stg.median_listing_price, stg.median_price_per_sqft,
            stg.median_days_on_market,
            stg.total_listings, stg.new_listings,
            stg.source, stg.batch_id, stg.ingested_at
        FROM REAL_ESTATE.STAGING.stg_fact_market_stats stg
        JOIN REAL_ESTATE.ANALYTICS.dim_location dim_loc
            ON  stg.city     = dim_loc.city
            AND stg.state    = dim_loc.state
            AND stg.zip_code = dim_loc.zip_code
        WHERE NOT EXISTS (
            SELECT 1 FROM REAL_ESTATE.ANALYTICS.fact_market_stats existing
            WHERE existing.batch_id = stg.batch_id
        );
        """,
    ]

    snowflake_execute(connection, queries)


def lambda_handler(event, context):
    execution_date = event.get(
        "execution_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )

    logger.info("Starting load data from S3 to Snowflake")

    with get_snowflake_conn() as connection:
        logger.info("Truncate temporary staging tables")
        truncate_staging(connection)

        logger.info("Loading data from S3 to Snowflake Staging schema")
        load_to_staging(connection, execution_date)
        merge_dim_location(connection)

        logger.info("Loading data from Snowflake Staging to Snowflake Analytics")
        insert_fact_tables(connection)

    summary = {
        "execution_date": execution_date,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(json.dumps(summary))

    return {"statusCode": 200, "body": summary}
