import logging
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

os.environ["BUCKET_NAME"] = "my-real-estate-pipeline-dev"
os.environ["SOURCE_KEY"] = "raw/kaggle/source/realtor-data.csv"
os.environ["AWS_PROFILE"] = "real-estate-dp"

from handler import lambda_handler                               
                                                                  
event = {"execution_date": "2024-01-01"}
result = lambda_handler(event, {})
print(result)