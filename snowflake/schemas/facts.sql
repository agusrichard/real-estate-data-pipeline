CREATE TABLE IF NOT EXISTS REAL_ESTATE.ANALYTICS.fact_listings (
    listing_id          INTEGER AUTOINCREMENT PRIMARY KEY,
    location_id         INTEGER       REFERENCES REAL_ESTATE.ANALYTICS.dim_location(location_id),
    property_type_id    INTEGER       REFERENCES REAL_ESTATE.ANALYTICS.dim_property_type(property_type_id),
    -- shared
    price               FLOAT,
    status              VARCHAR(50),
    source              VARCHAR(20)   NOT NULL,
    batch_id            VARCHAR(100)  NOT NULL,
    ingested_at         TIMESTAMP_TZ  NOT NULL,
    -- kaggle-specific (NULL for rentcast rows)
    bed                 FLOAT,
    bath                FLOAT,
    acre_lot            FLOAT,
    house_size          FLOAT,
    prev_sold_date      DATE,
    brokered_by         VARCHAR(200),
    -- rentcast-specific (NULL for kaggle rows)
    rentcast_id         VARCHAR(100),
    address             VARCHAR(200),
    bedrooms            FLOAT,
    bathrooms           FLOAT,
    square_footage      FLOAT,
    lot_size            FLOAT,
    latitude            FLOAT,
    longitude           FLOAT,
    days_on_market      INTEGER,
    listed_date         DATE
);

CREATE TABLE IF NOT EXISTS REAL_ESTATE.ANALYTICS.fact_market_stats (
    stat_id                     INTEGER AUTOINCREMENT PRIMARY KEY,
    location_id                 INTEGER       REFERENCES REAL_ESTATE.ANALYTICS.dim_location(location_id),
    snapshot_date               DATE,
    median_listing_price        FLOAT,
    median_price_per_sqft       FLOAT,
    median_days_on_market       FLOAT,
    total_listings              INTEGER,
    new_listings                INTEGER,
    source                      VARCHAR(20)   NOT NULL,
    batch_id                    VARCHAR(100)  NOT NULL,
    ingested_at                 TIMESTAMP_TZ  NOT NULL
);