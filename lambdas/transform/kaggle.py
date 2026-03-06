import polars as pl


def clean(df: pl.DataFrame) -> pl.DataFrame:
    # 1. Drop rows where price is missing or non-positive
    df = df.filter(pl.col("price").is_not_null() & (pl.col("price") > 0))

    # 2. Parse prev_sold_date; unparseable strings become null
    df = df.with_columns(
        pl.col("prev_sold_date").str.to_date(format="%Y-%m-%d", strict=False)
    )

    # 3. Remove price outliers over $100M
    df = df.filter(pl.col("price") <= 100_000_000)

    # 4. Drop rows where city, state, or zip_code are null/invalid
    df = df.filter(
        pl.col("city").is_not_null()
        & pl.col("state").is_not_null()
        & pl.col("zip_code").is_not_null()
        & (pl.col("zip_code") > 0)
    )

    # 5. Normalize city and state: strip whitespace, lowercase
    df = df.with_columns([
        pl.col("city").str.strip_chars().str.to_lowercase(),
        pl.col("state").str.strip_chars().str.to_lowercase(),
    ])

    return df


def build_dim_location(df: pl.DataFrame) -> pl.DataFrame:
    return (
      df.select(["city", "state", "zip_code"])
      .unique()
      .sort(["state", "city", "zip_code"])
      .with_row_index(name="location_id", offset=1)
    )
