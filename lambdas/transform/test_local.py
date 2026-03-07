import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

import uuid
from datetime import datetime, timezone

import polars as pl
from kaggle import transform

# Load a small sample from the real CSV
df = pl.read_csv(
    "../../inspect/realtor-data.csv",
    infer_schema_length=10_000,
    n_rows=1_000,
)

print(f"Rows before cleaning: {df.shape[0]}")

batch_id = str(uuid.uuid4())
ingested_at = datetime.now(timezone.utc).isoformat()

dim_location, dim_property_type, fact_listings = transform(df, batch_id, ingested_at)

print(f"Rows after cleaning (fact_listings): {fact_listings.shape[0]}")
print(f"dim_location rows: {dim_location.shape[0]}")
print(f"dim_property_type rows: {dim_property_type.shape[0]}")

# Verify no duplicate locations
assert dim_location.select(["city", "state", "zip_code"]).is_duplicated().sum() == 0, (
    "dim_location has duplicates!"
)

# Verify FK integrity
orphans = fact_listings.join(
    dim_location.select("location_id"),
    on="location_id",
    how="anti",
)
assert orphans.shape[0] == 0, f"Orphan location_ids found: {orphans.shape[0]}"

print("\ndim_property_type:")
print(dim_property_type)
print("\nfact_listings sample:")
print(fact_listings.head(5))
print("\nAll checks passed.")
