import polars as pl

from common.utils import (
    build_dim_location,
    build_dim_property_type,
    expand_state_abbr,
    normalize_address,
    validate_lat_long,
)

PROPERTY_TYPE_MAP = {
    "Single Family": "single_family",
    "Condo": "condo",
    "Townhouse": "townhouse",
    "Multi-Family": "multi_family",
}


def clean(df: pl.DataFrame) -> pl.DataFrame:
    df = df.filter(pl.col("id").is_not_null())
    df = df.rename({"zipCode": "zip_code"})
    df = df.with_columns(normalize_address(pl.col("addressLine1")).alias("address"))
    df = df.with_columns(expand_state_abbr(pl.col("state")))
    df = df.with_columns(pl.col("city").str.strip_chars().str.to_lowercase())
    df = validate_lat_long(df)
    return df


def build_fact_listings(
    df: pl.DataFrame,
    dim_location: pl.DataFrame,
    dim_property_type: pl.DataFrame,
    batch_id: str,
    ingested_at: str,
) -> pl.DataFrame:
    df = df.with_columns(
        pl.col("propertyType")
        .replace(PROPERTY_TYPE_MAP, default="unknown")
        .alias("property_type")
    )

    return (
        df.join(dim_location, on=["city", "state", "zip_code"], how="left")
        .join(dim_property_type, on=["property_type"], how="left")
        .rename(
            {
                "id": "rentcast_id",
                "squareFootage": "square_footage",
                "lotSize": "lot_size",
                "daysOnMarket": "days_on_market",
                "listedDate": "listed_date",
            }
        )
        .select(
            [
                "location_id",
                "property_type_id",
                "rentcast_id",
                "address",
                "price",
                "status",
                "bedrooms",
                "bathrooms",
                "square_footage",
                "lot_size",
                "latitude",
                "longitude",
                "days_on_market",
                "listed_date",
            ]
        )
        .with_columns(
            [
                pl.lit("rentcast").alias("source"),
                pl.lit(batch_id).alias("batch_id"),
                pl.lit(ingested_at).alias("ingested_at"),
            ]
        )
    )


def build_fact_market_stats(
    market_raw: dict,
    dim_location: pl.DataFrame,
    batch_id: str,
    ingested_at: str,
) -> pl.DataFrame:
    zip_code = market_raw["zipCode"]
    history = market_raw["saleData"]["history"]

    rows = [
        {
            "zip_code": zip_code,
            "snapshot_date": entry["date"],
            "median_listing_price": entry.get("medianPrice"),
            "median_price_per_sqft": entry.get("medianPricePerSquareFoot"),
            "median_days_on_market": entry.get("medianDaysOnMarket"),
            "total_listings": entry.get("totalListings"),
            "new_listings": entry.get("newListings"),
        }
        for entry in history.values()
    ]
    df = pl.DataFrame(rows)
    df = df.join(
        dim_location.select(["zip_code", "location_id"]), on="zip_code", how="left"
    )
    df = df.with_columns(
        [
            pl.col("snapshot_date").str.to_date(
                format="%Y-%m-%dT%H:%M:%S%.3fZ", strict=False
            ),
            pl.lit("rentcast").alias("source"),
            pl.lit(batch_id).alias("batch_id"),
            pl.lit(ingested_at).alias("ingested_at"),
        ]
    )
    return df.select(
        [
            "location_id",
            "snapshot_date",
            "median_listing_price",
            "median_price_per_sqft",
            "median_days_on_market",
            "total_listings",
            "new_listings",
            "source",
            "batch_id",
            "ingested_at",
        ]
    )


def transform(
    records: list[dict],
    market_raw: dict,
    batch_id: str,
    ingested_at: str,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    df = pl.DataFrame(records)
    df = clean(df)
    dim_location = build_dim_location(df)
    dim_property_type = build_dim_property_type()
    fact_listings = build_fact_listings(
        df, dim_location, dim_property_type, batch_id, ingested_at
    )
    fact_market_stats = build_fact_market_stats(
        market_raw, dim_location, batch_id, ingested_at
    )
    return dim_location, dim_property_type, fact_listings, fact_market_stats
