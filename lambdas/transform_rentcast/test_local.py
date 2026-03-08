import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rentcast import transform

SAMPLES = Path(__file__).parent.parent.parent / "docs/rentcast_response_examples"

with open(SAMPLES / "rentcast_property_listing.json") as f:
    records = json.load(f)

with open(SAMPLES / "rentcast_property_market.json") as f:
    market_raw = json.load(f)

print(f"Records loaded: {len(records)}")

batch_id = str(uuid.uuid4())
ingested_at = datetime.now(timezone.utc).isoformat()

dim_location, dim_property_type, fact_listings, fact_market_stats = transform(
    records, [market_raw], batch_id, ingested_at
)

print(f"fact_listings rows: {fact_listings.shape[0]}")
print(f"fact_market_stats rows: {fact_market_stats.shape[0]}")
print(f"dim_location rows: {dim_location.shape[0]}")
print(f"dim_property_type rows: {dim_property_type.shape[0]}")

# Verify no duplicate locations
assert dim_location.select(["city", "state", "zip_code"]).is_duplicated().sum() == 0, (
    "dim_location has duplicates!"
)

# Verify state format
assert dim_location["state"].str.len_chars().min() > 2, (
    "state values look like abbreviations, not full names"
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
print("\nfact_market_stats sample:")
print(fact_market_stats.head(5))
print("\nAll checks passed.")

# Write output Parquet files locally for inspection
os.makedirs("output", exist_ok=True)
dim_location.write_parquet("output/dim_location.parquet")
dim_property_type.write_parquet("output/dim_property_type.parquet")
fact_listings.write_parquet("output/fact_listings.parquet")
fact_market_stats.write_parquet("output/fact_market_stats.parquet")

print("\nParquet files written to lambdas/transform_rentcast/output/")
