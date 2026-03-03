import logging
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

os.environ["BUCKET_NAME"] = "my-real-estate-pipeline-dev"
os.environ["RENTCAST_SECRET_ID"] = "rentcast/api-key"
os.environ["TARGET_STATES"] = "AL"
os.environ["AWS_PROFILE"] = "real-estate-dp"

from handler import lambda_handler  # noqa: E402

event = {"execution_date": "2026-03-03", "states": ["AL"], "max_pages": 1}
result = lambda_handler(event, {})
print(result)
