# Design Decisions

Key architectural and technology choices made in this project, with rationale.

---

## Why Polars over Pandas?

AWS Lambda has a 10 GB memory ceiling and a 15-minute timeout. Polars uses Apache Arrow columnar format under the hood, giving 2-5x better memory efficiency and significantly faster execution than Pandas for the same operations. The Kaggle dataset (~2.2M rows) processes comfortably within Lambda's constraints using Polars, whereas Pandas would require a larger (and more expensive) memory allocation.

Polars also supports lazy evaluation, which lets the query optimizer push down filters and projections before materializing the full dataframe. This matters when reading large Parquet files from S3 — only the needed columns and rows are loaded into memory.

## Why Two Ingestion Lambdas?

Each data source has a fundamentally different extraction pattern:

- **Kaggle**: downloads a static CSV file from S3, writes it back to the raw zone. File-based, single-call.
- **RentCast**: paginated REST API with rate limits, multiple endpoints, and state-by-state iteration.

Separate Lambdas keep the code focused, independently deployable, and easier to debug. A failure in the RentCast API (rate limit, timeout) doesn't affect Kaggle ingestion. Each Lambda can also have its own memory/timeout configuration tuned to its workload.

## Why Separate Transform Lambdas per Source?

Each source has its own cleaning and normalization logic:

- **Kaggle**: deduplication, type casting, handling anonymized fields, mapping property types from free-text.
- **RentCast**: flattening nested API responses, extracting market statistics, handling nullable fields.

Keeping them separate means each transform Lambda is small, testable, and can run in parallel in the Airflow DAG. If one source's schema changes, only that transform needs updating.

## Why a Unified `fact_listings` Table?

Rather than separate fact tables per source, both Kaggle and RentCast listings go into a single `fact_listings` table with a `source` column. Source-specific columns are nullable (e.g., `rentcast_id` is NULL for Kaggle rows).

This simplifies analytical queries — you can compare across sources with a single `GROUP BY` and `CASE WHEN source = ...` instead of joining separate tables. It also makes the MERGE logic simpler: one target table per data category, not per source.

The tradeoff is a wider table with many nullable columns, but this is standard practice in data warehousing for multi-source integration.

## Why Aggregate-Level Joins?

The Kaggle dataset anonymizes street addresses, making property-level joins with RentCast data impossible. Instead, the two sources are joined at the geographic aggregate level (zip code, city, state) through the shared `dim_location` dimension.

This mirrors real-world scenarios where data sources don't share clean primary keys and enrichment must happen at a coarser grain. It's a deliberate design choice, not a limitation.

## Why MWAA over Self-Hosted Airflow?

Self-hosted Airflow requires managing a scheduler, webserver, metadata database (Postgres), workers, and potentially Celery/Redis — all on EC2 or ECS. MWAA wraps all of this behind a managed service with native AWS IAM integration, automatic version upgrades, and built-in CloudWatch logging.

The tradeoff is cost (~$0.49/hr for `mw1.small`), but for this project the convenience outweighs the cost. The MWAA environment can be torn down when not in use (`terraform destroy -target=module.mwaa`) and re-created in ~30 minutes.

## Why the Load Lambda Instead of SnowflakeOperator?

The load step runs as a Lambda function rather than using Airflow's `SnowflakeOperator` directly. This keeps all Snowflake SQL logic (COPY INTO, MERGE, metadata logging, quality checks) centralized in one place — the Lambda — rather than split between Lambda code and Airflow DAG code.

It also means the Airflow DAG doesn't need Snowflake credentials or the Snowflake provider package. The DAG is purely an orchestrator: it decides when things run and in what order, not how they run.

## Why an S3 Staging Zone?

The transform Lambdas write cleaned Parquet files to `s3://bucket/staging/` rather than loading directly into Snowflake. This provides a checkpoint between transform and load:

- If the Snowflake load fails, you can re-load from staging without re-transforming.
- You can inspect staged data independently to determine whether an issue is in the transform or load step.
- Snowflake's COPY INTO reads directly from S3, which is its most efficient loading path.

## Why Terraform Modules?

Each infrastructure concern (S3, Lambda, IAM, MWAA, Snowflake IAM) is its own Terraform module. This provides:

- **Reuse**: the Lambda module is used five times with different parameters.
- **Isolation**: changes to MWAA networking don't risk breaking the S3 bucket config.
- **Readability**: the root `main.tf` reads like a high-level architecture description.

## Why Star Schema?

A star schema (dimension + fact tables) was chosen over a flat denormalized table because:

- It avoids data redundancy (location data stored once in `dim_location`, not repeated in every fact row).
- It supports multiple fact tables (`fact_listings`, `fact_market_stats`) joined through shared dimensions.
- It's the standard pattern for analytical workloads in Snowflake and familiar to anyone reviewing the project.

## Why Not dbt?

dbt would be a natural addition for managing Snowflake transformations, testing, and documentation. It was intentionally omitted to keep the project scope manageable. The current approach (SQL scripts + Lambda-based loading) demonstrates the same concepts. Adding dbt is a logical next step.
