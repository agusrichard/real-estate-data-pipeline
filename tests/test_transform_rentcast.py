import polars as pl

from conftest import load_module

rentcast = load_module(
    "lambdas/transform_rentcast/rentcast.py", "rentcast", ["lambdas"]
)
kaggle = load_module("lambdas/transform_kaggle/kaggle.py", "kaggle", ["lambdas"])


def make_record(**overrides) -> dict:
    base = {
        "id": "123-Main-St,-Austin,-TX-78701",
        "addressLine1": "123 Main Street",
        "city": "Austin",
        "state": "TX",
        "zipCode": "78701",
        "latitude": 30.267,
        "longitude": -97.743,
        "propertyType": "Single Family",
        "price": 350_000,
        "status": "Active",
        "bedrooms": 3,
        "bathrooms": 2,
        "squareFootage": 1800,
        "lotSize": 5000,
        "daysOnMarket": 30,
        "listedDate": "2024-01-15T00:00:00.000Z",
    }
    base.update(overrides)
    return base


def make_market_raw(zip_code: str = "78701", n_months: int = 3) -> dict:
    history = {
        f"2025-0{i}": {
            "date": f"2025-0{i}-01T00:00:00.000Z",
            "medianPrice": 300_000 + i * 1000,
            "medianPricePerSquareFoot": 180.0,
            "medianDaysOnMarket": 40,
            "totalListings": 100,
            "newListings": 10,
        }
        for i in range(1, n_months + 1)
    }
    return {"zipCode": zip_code, "saleData": {"history": history}}


BATCH_ID = "test-batch"
INGESTED_AT = "2026-01-01T00:00:00+00:00"


# --- clean ---


def test_clean_drops_null_id():
    df = pl.DataFrame([make_record(id=None)])
    assert rentcast.clean(df).shape[0] == 0


def test_clean_renames_zip_code():
    df = pl.DataFrame([make_record()])
    result = rentcast.clean(df)
    assert "zip_code" in result.columns
    assert "zipCode" not in result.columns


def test_clean_expands_state_abbr():
    df = pl.DataFrame([make_record(state="TX")])
    result = rentcast.clean(df)
    assert result["state"][0] == "texas"


def test_clean_lowercases_city():
    df = pl.DataFrame([make_record(city="Austin")])
    result = rentcast.clean(df)
    assert result["city"][0] == "austin"


# --- build_fact_listings / property type mapping ---


def test_property_type_mapping():
    records = [
        make_record(propertyType="Single Family"),
        make_record(id="2", propertyType="Condo"),
        make_record(id="3", propertyType="Townhouse"),
        make_record(id="4", propertyType="Multi-Family"),
        make_record(id="5", propertyType="Land"),
    ]
    df = pl.DataFrame(records)
    df = rentcast.clean(df)
    dim_loc = rentcast.build_dim_location(df)
    dim_pt = rentcast.build_dim_property_type()
    fact = rentcast.build_fact_listings(df, dim_loc, dim_pt, BATCH_ID, INGESTED_AT)

    from common.utils import build_dim_property_type

    assert set(fact["property_type_id"].drop_nulls().to_list()).issubset(
        set(build_dim_property_type()["property_type_id"].to_list())
    )


# --- dim_location ---


def test_dim_location_no_duplicates():
    records = [
        make_record(id="1", city="Austin", state="TX", zipCode="78701"),
        make_record(id="2", city="Austin", state="TX", zipCode="78701"),  # duplicate
        make_record(id="3", city="Dallas", state="TX", zipCode="75201"),
    ]
    df = pl.DataFrame(records)
    df = rentcast.clean(df)
    dim_loc = rentcast.build_dim_location(df)
    assert dim_loc.select(["city", "state", "zip_code"]).is_duplicated().sum() == 0


# --- fact_listings FK integrity ---


def test_fact_foreign_key_integrity():
    records = [make_record(), make_record(id="2", city="Dallas", zipCode="75201")]
    df = pl.DataFrame(records)
    df = rentcast.clean(df)
    dim_loc = rentcast.build_dim_location(df)
    dim_pt = rentcast.build_dim_property_type()
    fact = rentcast.build_fact_listings(df, dim_loc, dim_pt, BATCH_ID, INGESTED_AT)

    orphans = fact.join(dim_loc.select("location_id"), on="location_id", how="anti")
    assert orphans.shape[0] == 0


# --- fact_market_stats ---


def test_market_stats_row_count():
    n_months = 5
    market_raw = make_market_raw(n_months=n_months)
    dim_loc = pl.DataFrame(
        {
            "location_id": [1],
            "city": ["austin"],
            "state": ["texas"],
            "zip_code": ["78701"],
        }
    )
    result = rentcast.build_fact_market_stats(
        [market_raw], dim_loc, BATCH_ID, INGESTED_AT
    )
    assert result.shape[0] == n_months


def test_market_stats_empty_when_no_data():
    dim_loc = pl.DataFrame(
        {
            "location_id": [1],
            "city": ["austin"],
            "state": ["texas"],
            "zip_code": ["78701"],
        }
    )
    result = rentcast.build_fact_market_stats([], dim_loc, BATCH_ID, INGESTED_AT)
    assert result.shape[0] == 0


# --- audit columns ---


def test_audit_columns_present():
    records = [make_record()]
    df = pl.DataFrame(records)
    df = rentcast.clean(df)
    dim_loc = rentcast.build_dim_location(df)
    dim_pt = rentcast.build_dim_property_type()
    fact = rentcast.build_fact_listings(df, dim_loc, dim_pt, BATCH_ID, INGESTED_AT)

    for col in ["source", "batch_id", "ingested_at"]:
        assert col in fact.columns
    assert fact["source"][0] == "rentcast"
    assert fact["batch_id"][0] == BATCH_ID


# --- schema alignment with Kaggle ---


def test_schema_alignment_with_kaggle():
    rc_records = [make_record()]
    rc_df = pl.DataFrame(rc_records)
    rc_df = rentcast.clean(rc_df)
    rc_dim_loc = rentcast.build_dim_location(rc_df)

    kg_df = pl.DataFrame(
        {
            "brokered_by": [1.0],
            "status": ["for_sale"],
            "price": [300_000.0],
            "bed": [3.0],
            "bath": [2.0],
            "acre_lot": [0.1],
            "street": [123.0],
            "city": ["Austin"],
            "state": ["Texas"],
            "zip_code": [78701.0],
            "house_size": [1500.0],
            "prev_sold_date": ["2020-01-15"],
        }
    )
    kg_df = kaggle.clean(kg_df)
    kg_dim_loc = kaggle.build_dim_location(kg_df)

    assert rc_dim_loc.schema == kg_dim_loc.schema

    combined = pl.concat(
        [
            kg_dim_loc.select(["city", "state", "zip_code"]),
            rc_dim_loc.select(["city", "state", "zip_code"]),
        ]
    ).unique()
    assert combined.shape[0] > 0
