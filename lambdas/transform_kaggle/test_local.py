import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))  # makes lambdas/common importable

# isort: split
import logging  # noqa: E402
import uuid  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import polars as pl  # noqa: E402
from kaggle import transform  # noqa: E402


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# Load a small sample from the real CSV as a LazyFrame (matches Lambda behaviour)
lf = pl.scan_csv(
    HERE / "../../inspect/realtor-data.csv",
    infer_schema_length=10_000,
    n_rows=1_000,
)

batch_id = str(uuid.uuid4())
ingested_at = datetime.now(timezone.utc).isoformat()

dim_location, dim_property_type, fact_listings = transform(lf, batch_id, ingested_at)

print(f"Rows after cleaning (fact_listings): {fact_listings.shape[0]}")  # noqa: E501
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

# Write output Parquet files locally for inspection
output_dir = HERE / "output"
output_dir.mkdir(exist_ok=True)
dim_location.write_parquet(output_dir / "dim_location.parquet")
dim_property_type.write_parquet(output_dir / "dim_property_type.parquet")
fact_listings.write_parquet(output_dir / "fact_listings.parquet")

print("\nParquet files written to lambdas/transform_kaggle/output/")
