import json
import logging
import os
import uuid
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
        role="PIPELINE_ROLE",
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
    merge_sql = """
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

    with connection.cursor() as cursor:
        cursor.execute(merge_sql)
        return cursor.rowcount


def insert_fact_tables(connection):
    kaggle_insert_sql = """
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
        JOIN REAL_ESTATE.STAGING.stg_dim_location stg_loc
            ON stg.location_id = stg_loc.location_id
        JOIN REAL_ESTATE.ANALYTICS.dim_location dim_loc
            ON  stg_loc.city     = dim_loc.city
            AND stg_loc.state    = dim_loc.state
            AND stg_loc.zip_code = dim_loc.zip_code
        WHERE NOT EXISTS (
            SELECT 1 FROM REAL_ESTATE.ANALYTICS.fact_listings existing
            WHERE existing.batch_id = stg.batch_id
        );
        """
    rentcast_insert_sql = """
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
        JOIN REAL_ESTATE.STAGING.stg_dim_location stg_loc
            ON stg.location_id = stg_loc.location_id
        JOIN REAL_ESTATE.ANALYTICS.dim_location dim_loc
            ON  stg_loc.city     = dim_loc.city
            AND stg_loc.state    = dim_loc.state
            AND stg_loc.zip_code = dim_loc.zip_code
        WHERE NOT EXISTS (
            SELECT 1 FROM REAL_ESTATE.ANALYTICS.fact_listings existing
            WHERE existing.batch_id = stg.batch_id
        );
    """
    market_stats_insert_sql = """
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
        JOIN REAL_ESTATE.STAGING.stg_dim_location stg_loc
            ON stg.location_id = stg_loc.location_id
        JOIN REAL_ESTATE.ANALYTICS.dim_location dim_loc
            ON  stg_loc.city     = dim_loc.city
            AND stg_loc.state    = dim_loc.state
            AND stg_loc.zip_code = dim_loc.zip_code
        WHERE NOT EXISTS (
            SELECT 1 FROM REAL_ESTATE.ANALYTICS.fact_market_stats existing
            WHERE existing.batch_id = stg.batch_id
        );
    """

    with connection.cursor() as cursor:
        cursor.execute(kaggle_insert_sql)
        kaggle_rows = cursor.rowcount

        cursor.execute(rentcast_insert_sql)
        rentcast_rows = cursor.rowcount

        cursor.execute(market_stats_insert_sql)
        market_rows = cursor.rowcount

    return kaggle_rows, rentcast_rows, market_rows


def insert_pipeline_metadata(
    connection, batch_id, source, table_name, row_count, start_time, status="SUCCESS"
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO REAL_ESTATE.ANALYTICS.pipeline_metadata
                (batch_id, source, table_name, row_count,
                 load_started_at, load_ended_at, status)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP(), %s)
            """,
            (batch_id, source, table_name, row_count, start_time, status),
        )


def run_quality_checks(connection, batch_id):
    QUALITY_CHECKS = [
        {
            "name": "null_price_fact_listings",
            "sql": """
                   SELECT COUNT(*)
                   FROM REAL_ESTATE.ANALYTICS.fact_listings
                   WHERE price IS NULL
                   """,
            "max_allowed": 0,
        },
        {
            "name": "orphan_fk_location_fact_listings",
            "sql": """
                    SELECT COUNT(*)
                    FROM REAL_ESTATE.ANALYTICS.fact_listings f
                    LEFT JOIN REAL_ESTATE.ANALYTICS.dim_location l
                    ON f.location_id = l.location_id
                    WHERE l.location_id IS NULL
                   """,
            "max_allowed": 0,
        },
        {
            "name": "orphan_fk_location_fact_market_stats",
            "sql": """
                    SELECT COUNT(*)
                    FROM REAL_ESTATE.ANALYTICS.fact_market_stats f
                    LEFT JOIN REAL_ESTATE.ANALYTICS.dim_location l
                    ON f.location_id = l.location_id
                    WHERE l.location_id IS NULL
                   """,
            "max_allowed": 0,
        },
        {
            "name": "null_location_fields_dim_location",
            "sql": """
                   SELECT COUNT(*)
                   FROM REAL_ESTATE.ANALYTICS.dim_location
                   WHERE city IS NULL
                      OR state IS NULL
                      OR zip_code IS NULL
                   """,
            "max_allowed": 0,
        },
    ]

    results = []
    with connection.cursor() as cursor:
        for check in QUALITY_CHECKS:
            sql = check["sql"]
            cursor.execute(sql)
            value = cursor.fetchone()[0]
            passed = value <= check["max_allowed"]
            cursor.execute(
                """
                   INSERT INTO REAL_ESTATE.ANALYTICS.data_quality_log
                       (batch_id, check_name, check_sql, result_value, passed)
                   VALUES (%s, %s, %s, %s, %s)
                """,
                (batch_id, check["name"], sql, value, passed),
            )
            results.append({"name": check["name"], "value": value, "passed": passed})
    return results


def lambda_handler(event, context):
    batch_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    execution_date = event.get(
        "execution_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )

    logger.info("Starting load data from S3 to Snowflake")

    try:
        quality_checks_result = None
        with get_snowflake_conn() as connection:
            logger.info("Truncate temporary staging tables")
            truncate_staging(connection)

            logger.info("Loading data from S3 to Snowflake Staging schema")
            load_to_staging(connection, execution_date)
            dim_location_rows = merge_dim_location(connection)

            logger.info("Loading data from Snowflake Staging to Snowflake Analytics")
            kaggle_rows, rentcast_rows, market_rows = insert_fact_tables(connection)

            logger.info("Logging pipeline metadata")
            insert_pipeline_metadata(
                connection,
                batch_id,
                "all",
                "dim_location",
                dim_location_rows,
                start_time,
            )
            insert_pipeline_metadata(
                connection,
                batch_id,
                "kaggle",
                "fact_listings",
                kaggle_rows,
                start_time,
            )
            insert_pipeline_metadata(
                connection,
                batch_id,
                "rentcast",
                "fact_listings",
                rentcast_rows,
                start_time,
            )
            insert_pipeline_metadata(
                connection,
                batch_id,
                "rentcast",
                "fact_market_stats",
                market_rows,
                start_time,
            )

            quality_checks_result = run_quality_checks(connection, batch_id)

    except Exception as e:
        logger.error(f"Load failed: {e}")
        with get_snowflake_conn() as connection:
            insert_pipeline_metadata(
                connection, batch_id, "all", "pipeline", 0, start_time, status="FAILED"
            )
        raise

    summary = {
        "execution_date": execution_date,
        "batch_id": batch_id,
        "rows_loaded": {
            "dim_location": dim_location_rows,
            "fact_listings_kaggle": kaggle_rows,
            "fact_listings_rentcast": rentcast_rows,
            "fact_market_stats": market_rows,
        },
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "quality_checks_result": quality_checks_result,
    }

    logger.info(json.dumps(summary))

    return {"statusCode": 200, "body": summary}
