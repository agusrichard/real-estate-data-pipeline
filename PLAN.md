# Build Plan

A step-by-step plan for building the real-estate-data-pipeline project solo, organized into step-sized milestones. Each milestone is designed to produce a working, testable increment.

---

## Phase 0: AWS Prerequisites (Before Any Code)

See [`plans/plan_phase0.md`](plans/plan_phase0.md) for the full setup steps.

---

## Phase 1: Foundation (Steps 1–2)

The goal of this phase is to set up the project skeleton, provision core AWS infrastructure with Terraform, and get raw data flowing into S3.

### Step 1: Project Setup & Terraform Foundation

**Objective:** Repository structure, Terraform scaffolding, and core AWS resources.

- [ ] Initialize the Git repository with the folder structure from the README
- [ ] Create `.gitignore` (Python, Terraform, IDE files, `.env`, data files)
- [ ] Set up `pyproject.toml` with project dependencies (polars, boto3, requests, etc.)
- [ ] Write Terraform configuration for foundational resources:
  - S3 bucket with folder structure (`raw/kaggle/`, `raw/rentcast/`, `staging/kaggle/`, `staging/rentcast/`, `errors/`)
  - S3 bucket versioning and lifecycle rules (expire old raw files after 90 days)
  - IAM roles and policies for Lambda execution (S3 read/write, CloudWatch logs)
  - AWS provider configuration and backend state (use S3 + DynamoDB for remote state)
- [ ] Organize Terraform into modules: `modules/s3`, `modules/iam`
- [ ] Create `environments/dev.tfvars` with development configuration
- [ ] Run `terraform plan` and `terraform apply` to verify everything provisions correctly
- [ ] Commit: _"feat: project skeleton and core AWS infrastructure"_

**Checkpoint:** You should be able to run `terraform apply` cleanly and see the S3 bucket in the AWS console.

### Step 2: Lambda Infrastructure & Kaggle Ingestion

**Objective:** Deploy the first Lambda function that downloads and lands the Kaggle CSV in S3.

- [ ] Download the Kaggle USA Real Estate Dataset locally and explore it
  - Understand the columns, data types, null patterns, and row count
  - Note: `street` and `brokered_by` are anonymized integers, not real addresses
  - Note: `prev_sold_date` has many nulls, `house_size` has ~30% nulls
- [ ] Write the Kaggle ingestion Lambda (`lambdas/ingest_kaggle/handler.py`):
  - Read the CSV from a source location (could be a pre-uploaded S3 location or bundled)
  - Split into date-partitioned chunks to simulate incremental ingestion (e.g., by state or row ranges)
  - Write each chunk as Parquet to `s3://bucket/raw/kaggle/YYYY-MM-DD/`
  - Add metadata: `ingested_at` timestamp, `source: kaggle`, `batch_id`
- [ ] Write Terraform for the Lambda:
  - `modules/lambda/` with function definition, layers, timeout, memory settings
  - Lambda layer for Polars (or use a container image if the layer exceeds 250MB)
  - Environment variables for bucket name and configuration
- [ ] Test locally first using `python-lambda-local` or a simple script that mimics the Lambda event
- [ ] Deploy with `terraform apply` and test with a manual invocation from the AWS console
- [ ] Commit: _"feat: Kaggle ingestion Lambda with S3 landing"_

**Checkpoint:** After invoking the Lambda, you should see Parquet files in `s3://bucket/raw/kaggle/` and be able to query them with AWS Athena or download and inspect locally.

---

## Phase 2: Data Extraction (Steps 3–4)

The goal of this phase is to complete the extraction layer by adding the RentCast API integration and establishing the two-source ingestion pattern.

### Step 3: RentCast API Ingestion Lambda

**Objective:** Second Lambda that calls the RentCast API and lands JSON responses in S3.

- [ ] Sign up for a free RentCast account and generate an API key
- [ ] Explore the API using Postman or curl:
  - Test `/properties` endpoint with a sample zip code
  - Test `/listings/sale` endpoint
  - Test `/market-statistics` endpoint
  - Understand rate limits and response schemas
- [ ] Design a strategy to maximize the 50 free calls/month:
  - Pick 3–5 target zip codes that overlap with the Kaggle dataset
  - Allocate calls: ~20 for property records, ~15 for sale listings, ~15 for market stats
  - Store the target zip codes in a config file or Lambda environment variable
- [ ] Write the RentCast ingestion Lambda (`lambdas/ingest_rentcast/handler.py`):
  - Accept an event payload specifying which endpoint and zip codes to call
  - Handle pagination for listing endpoints (up to 500 results per page)
  - Write raw JSON responses to `s3://bucket/raw/rentcast/YYYY-MM-DD/{endpoint}/`
  - Implement error handling: retry on 429 (rate limit), log failures
  - Track API call count to avoid exceeding the monthly quota
- [ ] Add Terraform for:
  - The new Lambda function
  - AWS Secrets Manager for the RentCast API key (don't hardcode it)
  - IAM policy for Secrets Manager access
- [ ] Test with a manual invocation, verify JSON files land in S3
- [ ] Commit: _"feat: RentCast API ingestion Lambda"_

**Checkpoint:** Both Lambdas work independently. You have Parquet files from Kaggle and JSON files from RentCast sitting in separate S3 prefixes.

### Step 4: Extraction Polish & Testing

**Objective:** Add operational polish, idempotency, and tests to both ingestion Lambdas.

- [ ] Add CloudWatch alarms:
  - Lambda error rate > 0 → SNS notification
  - Lambda duration approaching timeout → warning
- [ ] Implement idempotency in both Lambdas:
  - Check if today's partition already exists in S3 before re-processing
  - Use consistent naming: `s3://bucket/raw/{source}/{date}/{endpoint}_{batch_id}.parquet`
- [ ] Add basic logging structured as JSON (timestamp, source, records_count, status)
- [ ] Write unit tests for the extraction logic:
  - `tests/test_ingest.py`: mock the API responses and S3 writes
  - Test error handling paths (API timeout, malformed response, S3 write failure)
- [ ] Commit: _"feat: extraction monitoring, idempotency, and tests"_

**Note:** Scheduling is handled by MWAA (Phase 5), not EventBridge. During this phase, Lambdas are tested via manual invocation.

**Checkpoint:** Both Lambdas are robust, idempotent, and well-tested. CloudWatch shows structured execution logs.

---

## Phase 3: Transformation (Steps 5–6)

The goal of this phase is to build the Polars transformation logic that normalizes both sources into a consistent schema ready for Snowflake.

### Step 5: Kaggle Transformation Logic

**Objective:** Transform raw Kaggle data into cleaned, normalized tables.

- [ ] Write the core transformation logic (`lambdas/transform/handler.py` or a standalone module):
  - Read raw Parquet files from `s3://raw/kaggle/` using Polars
  - **Cleaning steps:**
    - Drop rows where `price` is null or <= 0
    - Drop rows where `bed` and `bath` are both null
    - Cast `prev_sold_date` to proper date type, handle nulls
    - Normalize `state` values (full name → abbreviation, or vice versa, pick one)
    - Remove obvious outliers (e.g., price > $100M, bed > 20)
    - Trim and lowercase `city` and `state` for consistency
  - **Dimension extraction:**
    - Extract `dim_location`: unique combinations of (city, state, zip_code), assign surrogate keys
    - Extract `dim_property_type`: derive property type from bed/bath/size patterns (since Kaggle doesn't have an explicit type field)
  - **Fact table construction:**
    - Build `fact_listings` with foreign keys to dimensions
    - Add `ingested_at`, `source`, and `batch_id` audit columns
  - Write output as Parquet to `s3://staging/kaggle/`
- [ ] Test the transformation locally with a sample of the data:
  - Verify row counts before and after cleaning
  - Verify dimension tables have no duplicates
  - Verify foreign key integrity
- [ ] Write unit tests: `tests/test_transform.py`
  - Test each cleaning rule in isolation
  - Test dimension extraction logic
  - Test with edge cases (all nulls, extreme values)
- [ ] Commit: _"feat: Kaggle data transformation with Polars"_

**Checkpoint:** Staging zone has clean, well-typed Parquet files with a consistent schema. You can load a sample into a notebook and verify the data looks correct.

### Step 6: RentCast Transformation & Schema Alignment

**Objective:** Transform RentCast JSON and align both sources to shared dimensions.

- [ ] Write transformation logic for RentCast data:
  - Read raw JSON files from `s3://raw/rentcast/` using Polars
  - **Flatten nested JSON:**
    - Property records: extract top-level fields + nested `features`, `taxAssessment`
    - Sale listings: extract listing fields + nested `history`, `contacts`
    - Market statistics: extract time-series data points
  - **Cleaning steps:**
    - Normalize address fields (standardize abbreviations: St/Street, Ave/Avenue)
    - Normalize `state` to match the Kaggle convention (same format chosen in Step 5)
    - Validate lat/long ranges (within continental US bounds)
    - Handle null valuations gracefully
  - **Build fact tables:**
    - `fact_property_details`: one row per property with AVM estimates, attributes, geolocation
    - `fact_market_stats`: one row per zip code per snapshot date
  - **Align with shared dimensions:**
    - Reuse `dim_location` generation logic — merge new zip codes from RentCast into the existing dimension
    - Reuse `dim_property_type` — map RentCast's `propertyType` field to the same categories
  - Write output to `s3://staging/rentcast/`
- [ ] Create a shared transformation utilities module:
  - `transform/utils.py`: common functions for state normalization, dimension key generation, data validation
  - Both Kaggle and RentCast transformations import from this shared module
- [ ] Verify schema alignment:
  - `dim_location` from both sources should be merge-able on (city, state, zip_code)
  - Both fact tables reference the same dimension key format
- [ ] Commit: _"feat: RentCast transformation and shared dimension alignment"_

**Checkpoint:** Staging zone now has consistently typed Parquet files from both sources. Dimensions are aligned and fact tables reference the same keys.

---

## Phase 4: Loading & Warehousing (Steps 7–8)

The goal of this phase is to set up Snowflake, load the staged data, and validate the end-to-end data flow.

### Step 7: Snowflake Setup & Data Loading

**Objective:** Create the Snowflake schema and load staged data.

- [ ] Set up Snowflake (use the free 30-day trial):
  - Create a database: `REAL_ESTATE`
  - Create schemas: `RAW`, `STAGING`, `ANALYTICS`
  - Create a warehouse: `TRANSFORM_WH` (X-Small, auto-suspend after 60s)
  - Create a service account role for the pipeline
- [ ] Write Snowflake DDL scripts (`snowflake/schemas/`):
  - `dimensions.sql`: `dim_location`, `dim_property_type` with proper keys and constraints
  - `facts.sql`: `fact_listings`, `fact_property_details`, `fact_market_stats`
  - `staging.sql`: staging tables matching the Parquet schemas (used for COPY INTO)
- [ ] Add Snowflake resources to Terraform:
  - Use the `Snowflake-Labs/snowflake` Terraform provider
  - Define database, schemas, warehouse, roles, and grants
  - Store Snowflake credentials in AWS Secrets Manager
- [ ] Build the loading logic using Snowflake's S3 external stage + COPY INTO:
  - Create an external stage pointing to `s3://bucket/staging/`
  - Use COPY INTO to load staged Parquet files into Snowflake staging tables
  - Implement upsert logic for dimensions (MERGE from staging tables into analytics tables)
  - Implement incremental append for fact tables (with deduplication on batch_id)
- [ ] Run a manual end-to-end test:
  - Trigger Kaggle Lambda → verify raw S3 → run transform → verify staging S3 → COPY INTO Snowflake
  - Query Snowflake to verify row counts and data integrity
- [ ] Commit: _"feat: Snowflake schema, Terraform resources, and data loading"_

**Checkpoint:** You can query `SELECT * FROM analytics.fact_listings LIMIT 10` in Snowflake and see clean, properly typed rows.

### Step 8: Snowflake Polish & Analytical Queries

**Objective:** Incremental loading, data quality checks, and sample analytics.

- [ ] Implement proper incremental loading:
  - Dimensions: MERGE (insert new, update changed)
  - Fact tables: INSERT only new records based on `batch_id` or `ingested_at`
  - Add a `pipeline_metadata` table tracking each load (batch_id, source, row_count, load_time)
- [ ] Add data quality checks in Snowflake:
  - Post-load validation queries (row count deltas, null checks on required fields, orphan foreign keys)
  - Store results in a `data_quality_log` table
- [ ] Write analytical queries (`snowflake/queries/analytics.sql`):
  - Average listing price by state (Kaggle)
  - AVM estimate distribution by property type (RentCast)
  - Price gap analysis: historical listing price vs current valuation by zip code
  - Market trends: median price over time by zip code (RentCast market stats)
  - Inventory analysis: listings per zip code, avg days on market
- [ ] Create a Snowflake view or materialized view for the joined aggregate analysis
- [ ] Commit: _"feat: incremental loading, data quality checks, and analytics"_

**Checkpoint:** Snowflake contains a complete, queryable dataset with clean dimensions, multiple fact tables, and working analytical queries.

---

## Phase 5: Orchestration (Steps 9–10)

The goal of this phase is to wire everything together with Airflow so the entire pipeline runs as a single, observable unit.

### Step 9: MWAA Setup & DAG

**Objective:** AWS MWAA environment running the full pipeline DAG.

- [ ] Add MWAA Terraform module (`modules/mwaa/`):
  - Create an S3 bucket for DAGs, plugins, and requirements.txt
  - Create the MWAA environment (environment class: `mw1.small` for dev)
  - Configure VPC networking (MWAA requires a VPC with private subnets and NAT gateway)
  - Create IAM execution role with permissions for S3, Lambda, CloudWatch, and Secrets Manager
  - Set Airflow configuration overrides (e.g., `core.default_timezone`)
  - Output the MWAA web UI URL
- [ ] Create `airflow/requirements.txt` with Python dependencies:
  - `apache-airflow-providers-snowflake`
  - Any additional packages needed by DAGs (provider packages for AWS are pre-installed in MWAA)
- [ ] Configure Airflow connections via MWAA environment variables or Secrets Manager:
  - `aws_default`: use the MWAA execution role (no explicit credentials needed)
  - `snowflake_default`: Snowflake account, user, role, warehouse (stored in Secrets Manager)
- [ ] Write the main DAG (`airflow/dags/real_estate_pipeline.py`):
  ```
  start
    │
    ├── ingest_kaggle_task (LambdaInvokeFunctionOperator)
    ├── ingest_rentcast_task (LambdaInvokeFunctionOperator)
    │
    └── (both complete) ──► s3_sensor_raw (S3KeySensor — wait for raw files)
                                │
                                ▼
                            transform_task (LambdaInvokeFunctionOperator)
                                │
                                ▼
                            s3_sensor_staging (S3KeySensor — wait for staged files)
                                │
                                ▼
                            load_dimensions_task (SnowflakeOperator — COPY INTO staging + MERGE dims)
                                │
                                ▼
                            load_facts_task (SnowflakeOperator — COPY INTO facts from S3 stage)
                                │
                                ▼
                            data_quality_task (SnowflakeOperator — run validation queries)
                                │
                                ▼
                            end
  ```
- [ ] Configure DAG settings:
  - Schedule: weekly (matching the RentCast call budget)
  - Retries: 2 with 5-minute delay
  - Catchup: False
  - Tags: `["real-estate", "production"]`
- [ ] Sync DAGs to the MWAA S3 bucket:
  - `aws s3 sync airflow/dags/ s3://<mwaa-bucket>/dags/`
  - `aws s3 cp airflow/requirements.txt s3://<mwaa-bucket>/requirements.txt`
- [ ] Test the DAG end-to-end via the MWAA Airflow UI
- [ ] Commit: _"feat: MWAA environment and DAG orchestrating full pipeline"_

**Checkpoint:** You can trigger the DAG from the MWAA Airflow UI and watch all tasks go green.

### Step 10: MWAA Polish & Error Handling

**Objective:** Make the orchestration production-ready.

- [ ] Add error handling and alerting:
  - `on_failure_callback` on each task to send notifications (email or Slack via webhook)
  - SLA alerts if the pipeline takes longer than expected
  - MWAA CloudWatch metrics and log groups for monitoring
- [ ] Add task-level documentation (each task has a `doc_md` attribute viewable in the UI)
- [ ] Parameterize the DAG:
  - Use Airflow Variables for target zip codes, batch sizes, and feature flags
  - Support manual trigger with parameters (e.g., run for a specific date range or zip code)
- [ ] Add idempotency at the DAG level:
  - Each run produces artifacts keyed by `execution_date`
  - Re-running a past date re-processes only that date's data
- [ ] Document the MWAA deployment choice in `docs/design_decisions.md`:
  - Why MWAA over self-hosted: no infrastructure to manage, native AWS IAM integration, automatic Airflow version upgrades, built-in CloudWatch logging
  - Tradeoff: higher cost (~$0.49/hr for mw1.small) but eliminates operational burden
- [ ] Commit: _"feat: production-ready MWAA with alerting and parameterization"_

**Checkpoint:** The pipeline is fully orchestrated on MWAA, handles failures gracefully, and can be re-run safely.

---

## Phase 6: Polish & Documentation (Steps 11–12)

The goal of this phase is to make the project portfolio-ready: clean code, comprehensive docs, and a compelling presentation.

### Step 11: Testing, CI, and Code Quality

**Objective:** Add tests, linting, and optional CI/CD.

- [ ] Expand test coverage:
  - Unit tests for all transformation functions
  - Integration test that runs the full pipeline against a small sample dataset
  - Test Terraform with `terraform validate` and `terraform plan`
- [ ] Add code quality tooling:
  - `ruff` for linting and formatting
  - `mypy` for type checking (Polars has good type stubs)
  - `pre-commit` hooks for automated checks before commits
- [ ] (Optional) Set up GitHub Actions:
  - On PR: run linting, type checks, and unit tests
  - On merge to main: run `terraform plan` and post the output as a PR comment
  - On merge to main: sync DAGs to the MWAA S3 bucket
- [ ] Clean up all TODO comments, dead code, and hardcoded values
- [ ] Commit: _"feat: test suite, linting, and CI pipeline"_

### Step 12: Final Documentation & README Polish

**Objective:** Make the repo shine for portfolio purposes.

- [ ] Finalize the README:
  - Add a screenshot or diagram of the Airflow DAG
  - Add a screenshot of the Snowflake query results
  - Ensure all setup instructions actually work from a clean clone
- [ ] Write `docs/design_decisions.md` covering:
  - Why Polars over Pandas (benchmark if possible)
  - Why aggregate-level joins instead of property-level
  - Terraform module structure rationale
  - Snowflake schema design choices (star schema vs normalized)
  - Airflow deployment choice and tradeoffs
- [ ] Add a `CONTRIBUTING.md` (optional but professional)
- [ ] Review every file in the repo for consistency and quality
- [ ] Do a final clean clone test: clone to a fresh directory and follow the README setup
- [ ] Commit: _"docs: final documentation and polish"_

**Checkpoint:** A stranger could clone the repo, read the README, and understand exactly what the project does, why it's built this way, and how to run it.

---

## Quick Reference: Accounts & Resources Needed

| Resource | Free Tier | Action Needed |
|---|---|---|
| AWS Account | 12-month free tier covers Lambda, S3 | Sign up, configure CLI |
| Snowflake | 30-day free trial ($400 credit) | Sign up, note the account URL |
| RentCast | 50 API calls/month | Sign up, generate API key |
| Kaggle | Free download | Download USA Real Estate Dataset |
| AWS MWAA | Included in AWS (pay per hour) | Provisioned via Terraform |
| Terraform | Free (open source) | Install via brew or binary |

## Tips for Staying on Track

- **Don't gold-plate early.** Get a working end-to-end pipeline first, then polish. A rough but complete pipeline is infinitely more impressive than a perfect extraction layer with nothing downstream.
- **Commit often with meaningful messages.** The commit history tells a story to anyone reviewing the repo.
- **If a step takes longer than expected, that's fine.** Shift the plan. The milestone boundaries are suggestions, not deadlines.
- **Test with small data first.** Don't try to load all 2.2M Kaggle rows until you've verified the pipeline works with 1,000 rows.
- **Keep a running list of "future improvements"** rather than getting sidetracked implementing them. These make great interview talking points ("I would add X next because...").