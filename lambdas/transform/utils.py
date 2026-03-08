import polars as pl
from common.constants import STATE_CODES

STREET_ABBR = {
    r"\bStreet\b": "St",
    r"\bAvenue\b": "Ave",
    r"\bBoulevard\b": "Blvd",
    r"\bDrive\b": "Dr",
    r"\bRoad\b": "Rd",
    r"\bLane\b": "Ln",
    r"\bCourt\b": "Ct",
}


STATE_ABBR_TO_NAME = {v.lower(): k.lower() for k, v in STATE_CODES.items()}


def normalize_state(series: pl.Expr) -> pl.Expr:
    return series.str.strip_chars().str.to_lowercase()


def assign_surrogate_keys(
    df: pl.DataFrame, key_col: str, offset: int = 1
) -> pl.DataFrame:
    return df.with_row_index(name=key_col, offset=offset)


def validate_lat_long(df: pl.DataFrame) -> pl.DataFrame:
    """
    Filter out rows with coordinates outside the continental US bounding box.

    Latitude must be between 24.0 and 49.5 degrees.
    Longitude must be between -125.0 and -66.0 degrees.

    Rows with null latitude or longitude are kept — a missing coordinate
    is not considered invalid.

    Args:
        df: Input DataFrame. Must contain 'latitude' and 'longitude' columns.

    Returns:
        DataFrame with out-of-bounds rows removed.
    """
    return df.filter(
        pl.col("latitude").is_null()
        | ((pl.col("latitude") >= 24.0) & (pl.col("latitude") <= 49.5))
    ).filter(
        pl.col("longitude").is_null()
        | ((pl.col("longitude") >= -125.0) & (pl.col("longitude") <= -66.0))
    )


def normalize_address(series: pl.Expr) -> pl.Expr:
    result = series
    for pattern, replacement in STREET_ABBR.items():
        result = result.str.replace(pattern, replacement)
    return result


def expand_state_abbr(col: pl.Expr) -> pl.Expr:
    """
    Convert a 2-letter state abbreviation (case-insensitive) to a lowercase full name.
    """
    return col.str.to_lowercase().replace(STATE_ABBR_TO_NAME)
