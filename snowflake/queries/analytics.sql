-- Average listing price by state from Kaggle data
SELECT l.state, AVG(f.price) AS avg_price, COUNT(*) AS listing_count
FROM REAL_ESTATE.ANALYTICS.fact_listings f
JOIN REAL_ESTATE.ANALYTICS.dim_location l ON f.location_id = l.location_id
WHERE f.source = 'kaggle'
GROUP BY l.state
ORDER BY avg_price DESC;

-- Price distribution by property type from RentCast data
SELECT pt.property_type, AVG(f.price) AS avg_price,
       MEDIAN(f.price) AS median_price, COUNT(*) AS listing_count
FROM REAL_ESTATE.ANALYTICS.fact_listings f
JOIN REAL_ESTATE.ANALYTICS.dim_property_type pt ON f.property_type_id = pt.property_type_id
WHERE f.source = 'rentcast'
GROUP BY pt.property_type
ORDER BY avg_price DESC;

-- Price gap: historical (Kaggle) vs current (RentCast) by zip code
SELECT
    l.zip_code, l.state,
    kaggle.avg_kaggle_price,
    rentcast.avg_rentcast_price,
    rentcast.avg_rentcast_price - kaggle.avg_kaggle_price AS price_gap,
    ROUND((rentcast.avg_rentcast_price - kaggle.avg_kaggle_price)
          / NULLIF(kaggle.avg_kaggle_price, 0) * 100, 2) AS pct_change
FROM REAL_ESTATE.ANALYTICS.dim_location l
JOIN (
    SELECT location_id, AVG(price) AS avg_kaggle_price
    FROM REAL_ESTATE.ANALYTICS.fact_listings WHERE source = 'kaggle'
    GROUP BY location_id
) kaggle ON l.location_id = kaggle.location_id
JOIN (
    SELECT location_id, AVG(price) AS avg_rentcast_price
    FROM REAL_ESTATE.ANALYTICS.fact_listings WHERE source = 'rentcast'
    GROUP BY location_id
) rentcast ON l.location_id = rentcast.location_id
ORDER BY pct_change DESC NULLS LAST;

-- Market trends: median listing price over time by zip code
SELECT l.zip_code, l.state, ms.snapshot_date,
       ms.median_listing_price, ms.median_days_on_market, ms.total_listings
FROM REAL_ESTATE.ANALYTICS.fact_market_stats ms
JOIN REAL_ESTATE.ANALYTICS.dim_location l ON ms.location_id = l.location_id
ORDER BY l.zip_code, ms.snapshot_date;

-- Inventory analysis: listings per zip code with avg days on market
SELECT l.zip_code, l.state, l.city,
       COUNT(*) AS listing_count,
       AVG(f.days_on_market) AS avg_days_on_market,
       AVG(f.price) AS avg_price
FROM REAL_ESTATE.ANALYTICS.fact_listings f
JOIN REAL_ESTATE.ANALYTICS.dim_location l ON f.location_id = l.location_id
WHERE f.source = 'rentcast' AND f.days_on_market IS NOT NULL
GROUP BY l.zip_code, l.state, l.city
ORDER BY listing_count DESC;
