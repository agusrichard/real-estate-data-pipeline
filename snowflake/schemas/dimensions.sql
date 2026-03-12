CREATE TABLE IF NOT EXISTS REAL_ESTATE.ANALYTICS.dim_location (
    location_id   INTEGER       NOT NULL,  -- assigned by Snowflake SEQUENCE
    city          VARCHAR(100)  NOT NULL,
    state         VARCHAR(50)   NOT NULL,
    zip_code      VARCHAR(10)   NOT NULL,
    CONSTRAINT pk_dim_location PRIMARY KEY (location_id),
    CONSTRAINT uq_dim_location UNIQUE (city, state, zip_code)
);

CREATE SEQUENCE IF NOT EXISTS REAL_ESTATE.ANALYTICS.dim_location_seq START = 1 INCREMENT = 1;

CREATE TABLE IF NOT EXISTS REAL_ESTATE.ANALYTICS.dim_property_type (
    property_type_id    INTEGER      NOT NULL,
    property_type       VARCHAR(50)  NOT NULL,
    CONSTRAINT pk_dim_property_type PRIMARY KEY (property_type_id),
    CONSTRAINT uq_dim_property_type UNIQUE (property_type)
);

-- Seed the lookup table (same 6 rows from utils.build_dim_property_type)
INSERT INTO REAL_ESTATE.ANALYTICS.dim_property_type VALUES
    (1, 'studio'),
    (2, 'single_family'),
    (3, 'multi_family'),
    (4, 'condo'),
    (5, 'townhouse'),
    (6, 'unknown');