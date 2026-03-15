CREATE
OR REPLACE VIEW REAL_ESTATE.ANALYTICS.v_price_comparison_by_zip AS
SELECT l.zip_code,
       l.state,
       l.city,
       kaggle.avg_kaggle_price,
       rentcast.avg_rentcast_price,
       rentcast.avg_rentcast_price - kaggle.avg_kaggle_price    AS price_gap,
       ROUND((rentcast.avg_rentcast_price - kaggle.avg_kaggle_price)
                 / NULLIF(kaggle.avg_kaggle_price, 0) * 100, 2) AS pct_change
FROM REAL_ESTATE.ANALYTICS.dim_location l
         LEFT JOIN (SELECT location_id, AVG(price) AS avg_kaggle_price
                    FROM REAL_ESTATE.ANALYTICS.fact_listings
                    WHERE source = 'kaggle'
                    GROUP BY location_id) kaggle ON l.location_id = kaggle.location_id
         LEFT JOIN (SELECT location_id, AVG(price) AS avg_rentcast_price
                    FROM REAL_ESTATE.ANALYTICS.fact_listings
                    WHERE source = 'rentcast'
                    GROUP BY location_id) rentcast ON l.location_id = rentcast.location_id
WHERE kaggle.avg_kaggle_price IS NOT NULL
   OR rentcast.avg_rentcast_price IS NOT NULL;

CREATE
OR REPLACE VIEW REAL_ESTATE.ANALYTICS.v_market_summary AS
SELECT l.zip_code,
       l.state,
       l.city,
       ms.snapshot_date,
       ms.median_listing_price,
       ms.median_price_per_sqft,
       ms.median_days_on_market,
       ms.total_listings,
       ms.new_listings
FROM REAL_ESTATE.ANALYTICS.fact_market_stats ms
         JOIN REAL_ESTATE.ANALYTICS.dim_location l ON ms.location_id = l.location_id QUALIFY ROW_NUMBER() OVER (PARTITION BY l.zip_code ORDER BY ms.snapshot_date DESC) = 1;
