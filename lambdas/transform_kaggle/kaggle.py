import polars as pl
from common.utils import build_dim_location, build_dim_property_type, normalize_state


def build_fact_listings(
    df: pl.DataFrame,
    dim_location: pl.DataFrame,
    dim_property_type: pl.DataFrame,
    batch_id: str,
    ingested_at: str,
) -> pl.DataFrame:
    df = df.with_columns(
        pl.when(pl.col("bed") == 0)
        .then(pl.lit("studio"))
        .when(pl.col("bed") <= 4)
        .then(pl.lit("single_family"))
        .when(pl.col("bed") >= 5)
        .then(pl.lit("multi_family"))
        .otherwise(pl.lit("unknown"))
        .alias("property_type")
    )

    return (
        df.join(dim_location, on=["city", "state", "zip_code"], how="left")
        .join(dim_property_type, on="property_type", how="left")
        .select(
            [
                "location_id",
                "property_type_id",
                "status",
                "price",
                "bed",
                "bath",
                "acre_lot",
                "house_size",
                "prev_sold_date",
                "brokered_by",
            ]
        )
        .with_columns(
            [
                pl.lit("kaggle").alias("source"),
                pl.lit(batch_id).alias("batch_id"),
                pl.lit(ingested_at).alias("ingested_at"),
            ]
        )
    )


def clean(df: pl.DataFrame) -> pl.DataFrame:
    # 1. Drop rows where price is missing or non-positive
    df = df.filter(pl.col("price").is_not_null() & (pl.col("price") > 0))

    # 2. Parse prev_sold_date; unparseable strings become null
    df = df.with_columns(
        pl.col("prev_sold_date").str.to_date(format="%Y-%m-%d", strict=False)
    )

    # 3. Remove price and bed outliers over $100M
    df = df.filter(pl.col("price") <= 100_000_000)
    df = df.filter(pl.col("bed").is_null() | (pl.col("bed") <= 20))

    # 4. Drop rows where city, state, or zip_code are null/invalid
    df = df.filter(
        pl.col("city").is_not_null()
        & pl.col("state").is_not_null()
        & pl.col("zip_code").is_not_null()
        & (pl.col("zip_code") > 0)
    )
    df = df.with_columns(pl.col("zip_code").cast(pl.String))

    # 5. Drop rows where both bed and bath are null
    df = df.filter(pl.col("bed").is_not_null() | pl.col("bath").is_not_null())

    # 6. Normalize city and state: strip whitespace, lowercase
    df = df.with_columns(
        [
            pl.col("city").str.strip_chars().str.to_lowercase(),
            normalize_state(pl.col("state")),
        ]
    )

    return df


def transform(
    df: pl.DataFrame,
    batch_id: str,
    ingested_at: str,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    df = clean(df)
    dim_location = build_dim_location(df)
    dim_property_type = build_dim_property_type()
    fact_listings = build_fact_listings(
        df, dim_location, dim_property_type, batch_id, ingested_at
    )
    return dim_location, dim_property_type, fact_listings
