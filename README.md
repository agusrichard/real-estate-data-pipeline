# Real Estate Data Pipeline

An end-to-end data pipeline that ingests property listing data from multiple sources, transforms it using modern tooling, and loads it into a cloud data warehouse for analysis. The entire infrastructure is defined as code and deployed on AWS.

## Overview

This project demonstrates a production-style ELT pipeline that combines two complementary real estate data sources:

- **Kaggle USA Real Estate Dataset** (~2.2M historical listings scraped from Realtor.com) — ingested as bulk CSV files, simulating a file-based data feed.
- **RentCast API** (live property records, valuations, and market statistics) — ingested via scheduled API calls, simulating a real-time data feed.

AWS MWAA (Managed Apache Airflow) orchestrates the entire flow: it triggers ingestion Lambdas on schedule, waits for raw data to land in S3, triggers transformation Lambdas that clean and normalize the data using Polars and write to an S3 staging zone, then loads the staged data into Snowflake via COPY INTO.

The two sources are normalized independently, loaded into a star schema in Snowflake, and joined at the **aggregate geographic level** (zip code, city, state) — not at the individual property level, since the Kaggle dataset has anonymized street addresses. This is a deliberate design choice that mirrors real-world scenarios where data sources don't share clean primary keys.

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                           AWS MWAA                                │
│                    (Managed Apache Airflow)                       │
│                                                                   │
│  Orchestrates the entire pipeline: schedules runs, triggers       │
│  Lambdas, monitors progress, loads Snowflake, handles retries     │
└───┬───────────────┬───────────────┬───────────────────┬───────────┘
    │ 1. Trigger    │ 1. Trigger    │ 3. Trigger        │ 5. Load into
    │    ingestion  │    ingestion  │    transformation │    Snowflake
    ▼               ▼               │                   │
┌─────────┐  ┌──────────┐           │                   │
│ Kaggle  │  │ RentCast │           │                   │
│ CSV     │  │ API      │           │                   │
└────┬────┘  └────┬─────┘           │                   │
     │            │                 │                   │
     ▼            ▼                 │                   │
┌─────────┐  ┌──────────┐           │                   │
│ Lambda  │  │ Lambda   │           │                   │
│ (Bulk   │  │ (API     │           │                   │
│ Ingest) │  │ Ingest)  │           │                   │
└────┬────┘  └────┬─────┘           │                   │
     │            │                 │                   │
     ▼            ▼                 │                   │
┌─────────────────────────┐         │                   │
│  Amazon S3 (Raw Zone)   │         │                   │
│  s3://bucket/raw/       │         │                   │
└────────────┬────────────┘         │                   │
             │ 2. Raw data          │                   │
             │    lands in S3       │                   │
             ▼                      ▼                   │
┌──────────────────────────────────────┐                │
│      Transformation Layer            │                │
│      (Polars on Lambda)              │                │
│                                      │                │
│  • Read raw data from S3             │                │
│  • Clean & deduplicate               │                │
│  • Normalize schemas                 │                │
│  • Build dimension conformity        │                │
│  • Write to S3 staging zone          │                │
└──────────────┬───────────────────────┘                │
               │ 4. Cleaned data                        │
               │    lands in S3                         │
               ▼                                        │
┌──────────────────────────────┐                        │
│  Amazon S3 (Staging Zone)    │                        │
│  s3://bucket/staging/        │                        │
└──────────────┬───────────────┘                        │
               │                                        │
               ▼                                        ▼
┌──────────────────────────────────────────────────────────┐
│                      Snowflake                           │
│                (COPY INTO from S3 stage)                 │
│                                                          │
│  dim_location  dim_property_type                         │
│  fact_listings  fact_property_details                    │
│  fact_market_stats                                       │
└──────────────────────────────────────────────────────────┘
```

## Data Sources

### Kaggle USA Real Estate Dataset

A static CSV dataset with ~2.2M US property listings. Used as the historical backbone of the pipeline.

| Column | Description |
|---|---|
| `brokered_by` | Anonymized broker/agent identifier |
| `status` | Listing status (for_sale, sold) |
| `price` | Listed or sold price (USD) |
| `bed` | Number of bedrooms |
| `bath` | Number of bathrooms |
| `acre_lot` | Lot size in acres |
| `street` | Anonymized street identifier |
| `city` | City name |
| `state` | State name |
| `zip_code` | ZIP code |
| `house_size` | Interior square footage |
| `prev_sold_date` | Previous sale date |

### RentCast API

A live REST API providing property records, valuations, and market data. Free tier allows 50 API calls/month.

Key endpoints used:
- `/properties` — Property records with structural attributes, geolocation, tax assessments
- `/avm/value` — Automated valuation model estimates with comparable properties
- `/listings/sale` — Active for-sale listings with price, days on market, listing contacts
- `/market-statistics` — Aggregate price and rent trends by zip code

Key fields returned include: `formattedAddress`, `city`, `state`, `zipCode`, `county`, `latitude`, `longitude`, `propertyType`, `bedrooms`, `bathrooms`, `squareFootage`, `lotSize`, `yearBuilt`, `lastSaleDate`, `lastSalePrice`.

### Why Two Sources?

The two datasets serve different roles and **cannot be joined at the property level** because Kaggle anonymizes street addresses. Instead, they are joined at the geographic aggregate level (zip code). This is intentional — it demonstrates a common real-world pattern where enrichment happens across mismatched schemas.

| Aspect | Kaggle CSV | RentCast API |
|---|---|---|
| **Volume** | ~2.2M rows | 50 calls/month (free tier) |
| **Freshness** | Static snapshot | Live / real-time |
| **Granularity** | Listing-level (anonymized) | Property-level (full address) |
| **Unique value** | Historical price distributions | Valuations, geolocation, market trends |
| **Ingestion pattern** | File-based (S3 upload) | API-based (Lambda HTTP calls) |

## Data Model

The pipeline outputs a star schema in Snowflake:

```
                    ┌──────────────────┐
                    │  dim_location    │
                    │                  │
                    │  location_key PK │
                    │  city            │
                    │  state           │
                    │  zip_code        │
                    │  county          │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼──────────────────────┐
         │                   │                      │
         ▼                   ▼                      ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│ fact_listings   │ │ fact_property   │ │ fact_market_stats   │
│ (from Kaggle)   │ │ _details        │ │ (from RentCast)     │
│                 │ │ (from RentCast) │ │                     │
│ listing_key  PK │ │                 │ │ market_stat_key PK  │
│ location_key FK │ │ property_key PK │ │ location_key    FK  │
│ property_type_  │ │ location_key FK │ │ snapshot_date       │
│   key        FK │ │ property_type_  │ │ median_sale_price   │
│ price           │ │   key        FK │ │ avg_rent            │
│ bed             │ │ bedrooms        │ │ avg_days_on_market  │
│ bath            │ │ bathrooms       │ │ inventory_count     │
│ house_size      │ │ sqft            │ │ price_trend_pct     │
│ acre_lot        │ │ lot_size        │ └─────────────────────┘
│ status          │ │ year_built      │
│ prev_sold_date  │ │ avm_estimate    │
│ ingested_at     │ │ last_sale_price │
└─────────────────┘ │ last_sale_date  │
                    │ latitude        │
                    │ longitude       │
                    └─────────────────┘
```

### Example Analytical Query

```sql
-- Compare historical listing prices vs current valuations by zip code
SELECT
    dl.zip_code,
    dl.city,
    dl.state,
    COUNT(fl.listing_key)       AS historical_listing_count,
    AVG(fl.price)               AS avg_historical_price,
    AVG(fpd.avm_estimate)       AS avg_current_valuation,
    AVG(fms.median_sale_price)  AS market_median_price,
    AVG(fpd.avm_estimate) - AVG(fl.price) AS price_appreciation
FROM fact_listings fl
JOIN dim_location dl ON fl.location_key = dl.location_key
LEFT JOIN fact_property_details fpd ON fpd.location_key = dl.location_key
LEFT JOIN fact_market_stats fms ON fms.location_key = dl.location_key
GROUP BY dl.zip_code, dl.city, dl.state
ORDER BY price_appreciation DESC;
```

## Tech Stack

| Tool | Role | Why This Tool |
|---|---|---|
| **AWS Lambda** | Compute for ingestion and transformation | Serverless, cost-effective for scheduled batch jobs. Polars runs well within Lambda's memory limits. |
| **Amazon S3** | Data lake (raw and staging zones) | Raw zone for ingested data, staging zone for cleaned/transformed data. Decouples each pipeline step and enables independent re-runs. |
| **Polars** | Data transformation | Faster and more memory-efficient than Pandas — critical inside Lambda's constraints. Lazy evaluation enables handling larger-than-memory datasets. |
| **Snowflake** | Cloud data warehouse | Separates compute from storage, handles semi-structured data natively, easy to demo with a free trial. |
| **AWS MWAA** | Orchestration and scheduling | Managed Apache Airflow service — no infrastructure to maintain, integrates natively with AWS IAM, S3, and CloudWatch. DAGs provide visibility, retry logic, and dependency management. |
| **Terraform** | Infrastructure as Code | Reproducible deployments, version-controlled infrastructure, demonstrates production-readiness. |
| **AWS (S3, Lambda, IAM, CloudWatch, MWAA)** | Cloud infrastructure | Full deployment story from code to running pipeline. |

## Repository Structure

```
real-estate-data-pipeline/
│
├── terraform/                  # Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── modules/
│   │   ├── s3/
│   │   ├── lambda/
│   │   ├── iam/
│   │   ├── mwaa/
│   │   └── snowflake/
│   └── environments/
│       ├── dev.tfvars
│       └── prod.tfvars
│
├── lambdas/                    # Lambda function source code
│   ├── ingest_kaggle/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── ingest_rentcast/
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── transform/
│       ├── handler.py
│       └── requirements.txt
│
├── airflow/                    # Airflow DAGs and config (deployed to MWAA S3 bucket)
│   ├── dags/
│   │   └── real_estate_pipeline.py
│   ├── plugins/
│   └── requirements.txt
│
├── snowflake/                  # Snowflake DDL and seed scripts
│   ├── schemas/
│   │   ├── dimensions.sql
│   │   ├── facts.sql
│   │   └── staging.sql
│   └── queries/
│       └── analytics.sql
│
├── tests/                      # Unit and integration tests
│   ├── test_ingest.py
│   ├── test_transform.py
│   └── test_load.py
│
├── docs/                       # Additional documentation
│   └── design_decisions.md
│
├── PLAN.md                     # Step-by-step build plan
├── README.md
├── .gitignore
└── pyproject.toml
```

## Getting Started

### Prerequisites

- AWS account with CLI configured
- Snowflake account (free trial works)
- RentCast API key (free tier: 50 calls/month)
- Terraform >= 1.5
- Python >= 3.11
- Docker (optional, for local Airflow testing)

### Setup

```bash
# Clone the repository
git clone https://github.com/<your-username>/real-estate-data-pipeline.git
cd real-estate-data-pipeline

# Download the Kaggle dataset
# Place realtor-data.zip.csv in data/raw/

# Set environment variables
export RENTCAST_API_KEY="your_api_key_here"
export SNOWFLAKE_ACCOUNT="your_account"
export SNOWFLAKE_USER="your_user"
export SNOWFLAKE_PASSWORD="your_password"

# Deploy infrastructure
cd terraform
terraform init
terraform plan -var-file="environments/dev.tfvars"
terraform apply -var-file="environments/dev.tfvars"

# Sync DAGs to MWAA S3 bucket (created by Terraform)
aws s3 sync airflow/dags/ s3://<mwaa-bucket>/dags/
aws s3 cp airflow/requirements.txt s3://<mwaa-bucket>/requirements.txt

# Trigger the pipeline
# Navigate to the MWAA Airflow UI (URL available in Terraform outputs)
# Enable and trigger the real_estate_pipeline DAG
```

## Design Decisions

- **Why Polars over Pandas?** Lambda has a 10GB memory ceiling. Polars uses Apache Arrow under the hood, giving 2-5x better memory efficiency and significantly faster execution for the transform step.
- **Why two ingestion Lambdas?** Each source has a fundamentally different extraction pattern (file download vs. paginated API). Separate Lambdas keep the code focused, independently deployable, and easier to debug.
- **Why aggregate-level joins?** The Kaggle dataset anonymizes street addresses, making property-level joins impossible. Joining on zip code mirrors real-world data enrichment where sources don't share clean foreign keys.
- **Why MWAA as the orchestrator?** MWAA triggers all pipeline steps (ingestion, transformation, loading) on a schedule via Airflow DAGs, replacing the need for EventBridge rules. This centralizes scheduling, retry logic, and monitoring in one place. MWAA is managed, so there's no infrastructure to maintain, and it integrates natively with AWS IAM and CloudWatch.
- **Why an S3 staging zone?** The transform Lambda writes cleaned Parquet to `s3://staging/` rather than loading directly into Snowflake. This provides a checkpoint between transform and load — if the Snowflake load fails, you can re-load from staging without re-transforming. It also makes debugging easier: you can inspect the staged data independently to determine whether an issue is in the transform or load step.
- **Why not dbt?** dbt would be a natural addition for the Snowflake transformation layer. It was intentionally omitted to keep the project scope manageable for a solo weekend project. It's a logical next step.

## Future Improvements

- Add dbt for in-warehouse transformation and data quality tests
- Build a Streamlit or Preset dashboard for visualization
- Add Great Expectations for data validation in the transform step
- Implement CI/CD with GitHub Actions for Lambda deployments and MWAA DAG syncing
- Add more RentCast endpoints (rental listings, rent estimates) as budget allows
- Implement SCD Type 2 for tracking property valuation changes over time