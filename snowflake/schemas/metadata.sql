CREATE TABLE IF NOT EXISTS REAL_ESTATE.ANALYTICS.pipeline_metadata (
    load_id         INTEGER AUTOINCREMENT PRIMARY KEY,
    batch_id        VARCHAR(255) NOT NULL,
    source          VARCHAR(50)  NOT NULL,  -- 'kaggle', 'rentcast'
    table_name      VARCHAR(255) NOT NULL,  -- e.g. 'fact_listings', 'dim_location'
    row_count       INTEGER      NOT NULL,
    load_started_at TIMESTAMP_NTZ NOT NULL,
    load_ended_at   TIMESTAMP_NTZ,
    status          VARCHAR(50)  NOT NULL DEFAULT 'SUCCESS'  -- 'SUCCESS', 'FAILED'
);

CREATE TABLE IF NOT EXISTS REAL_ESTATE.ANALYTICS.data_quality_log (
    check_id        INTEGER AUTOINCREMENT PRIMARY KEY,
    batch_id        VARCHAR(255) NOT NULL,
    check_name      VARCHAR(255) NOT NULL,  -- e.g. 'null_check_price', 'orphan_fk_location'
    check_sql       TEXT,
    result_value    INTEGER,                -- the count or metric returned
    passed          BOOLEAN NOT NULL,
    checked_at      TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP()
);