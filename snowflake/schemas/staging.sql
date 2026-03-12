-- Shared: both sources write dim_location and dim_property_type
CREATE TABLE IF NOT EXISTS REAL_ESTATE.STAGING.stg_dim_location (
    location_id   INTEGER,
    city          VARCHAR(100),
    state         VARCHAR(50),
    zip_code      VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS REAL_ESTATE.STAGING.stg_dim_property_type (
    property_type_id    INTEGER,
    property_type       VARCHAR(50)
);

-- Kaggle: staging/kaggle/{date}/fact_listings.parquet
CREATE TABLE IF NOT EXISTS REAL_ESTATE.STAGING.stg_fact_listings_kaggle (
    location_id         INTEGER,
    property_type_id    INTEGER,
    status              VARCHAR(50),
    price               FLOAT,
    bed                 FLOAT,
    bath                FLOAT,
    acre_lot            FLOAT,
    house_size          FLOAT,
    prev_sold_date      DATE,
    brokered_by         VARCHAR(200),
    source              VARCHAR(20),
    batch_id            VARCHAR(100),
    ingested_at         TIMESTAMP_TZ
);

-- RentCast: staging/rentcast/{date}/fact_listings.parquet
CREATE TABLE IF NOT EXISTS REAL_ESTATE.STAGING.stg_fact_listings_rentcast (
    location_id         INTEGER,
    property_type_id    INTEGER,
    rentcast_id         VARCHAR(100),
    address             VARCHAR(200),
    price               FLOAT,
    status              VARCHAR(50),
    bedrooms            FLOAT,
    bathrooms           FLOAT,
    square_footage      FLOAT,
    lot_size            FLOAT,
    latitude            FLOAT,
    longitude           FLOAT,
    days_on_market      INTEGER,
    listed_date         DATE,
    source              VARCHAR(20),
    batch_id            VARCHAR(100),
    ingested_at         TIMESTAMP_TZ
);

-- RentCast: staging/rentcast/{date}/fact_market_stats.parquet
CREATE TABLE IF NOT EXISTS REAL_ESTATE.STAGING.stg_fact_market_stats (
    location_id                 INTEGER,
    snapshot_date               DATE,
    median_listing_price        FLOAT,
    median_price_per_sqft       FLOAT,
    median_days_on_market       FLOAT,
    total_listings              INTEGER,
    new_listings                INTEGER,
    source                      VARCHAR(20),
    batch_id                    VARCHAR(100),
    ingested_at                 TIMESTAMP_TZ
);