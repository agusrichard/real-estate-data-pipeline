-- Run as ACCOUNTADMIN
USE ROLE ACCOUNTADMIN;

-- Storage integration: allows Snowflake to assume an IAM role to access S3
CREATE STORAGE INTEGRATION IF NOT EXISTS S3_INTEGRATION
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'S3'
  ENABLED = TRUE
  STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::585444021499:role/snowflake-s3-access-role'
  STORAGE_ALLOWED_LOCATIONS = ('s3://my-real-estate-pipeline-dev/staging/');

-- After creating, run this to get the values needed for the IAM trust policy:
-- DESC INTEGRATION S3_INTEGRATION;
-- Note: STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID

-- External stage: named pointer to the S3 staging prefix
CREATE STAGE IF NOT EXISTS REAL_ESTATE.STAGING.S3_STAGE
  STORAGE_INTEGRATION = S3_INTEGRATION
  URL = 's3://my-real-estate-pipeline-dev/staging/'
  FILE_FORMAT = (TYPE = PARQUET);
