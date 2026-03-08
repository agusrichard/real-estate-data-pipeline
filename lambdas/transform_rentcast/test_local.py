import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rentcast import transform

SAMPLES = Path(__file__).parent.parent.parent / "docs/rentcast_response_examples"

with open(SAMPLES / "rentcast_property_listing.json") as f:
    records = json.load(f)

with open(SAMPLES / "rentcast_property_market.json") as f:
    market_raw = json.load(f)

batch_id = "test-batch"
ingested_at = datetime.now(timezone.utc).isoformat()

dim_location, dim_property_type, fact_listings, fact_market_stats = transform(
    records, market_raw, batch_id, ingested_at
)

print("=== dim_location ===")
print(dim_location)

print("\n=== dim_property_type ===")
print(dim_property_type)

print("\n=== fact_listings ===")
print(fact_listings)

print("\n=== fact_market_stats ===")
print(fact_market_stats)

# Checks
assert dim_location.select(["city", "state", "zip_code"]).is_duplicated().sum() == 0, (
    "dim_location has duplicates!"
)
assert dim_location["state"].str.len_chars().min() > 2, (
    "state values look like abbreviations, not full names"
)
assert fact_listings["location_id"].null_count() < fact_listings.shape[0], (
    "all location_ids are null — join failed"
)
assert fact_market_stats.shape[0] > 0, "fact_market_stats is empty"

print("\nAll checks passed.")
