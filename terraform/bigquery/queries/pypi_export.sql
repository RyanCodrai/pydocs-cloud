-- Declare all variables at the beginning
DECLARE last_processed_timestamp TIMESTAMP;
DECLARE record_count INT64;
DECLARE unix_timestamp STRING;

-- Set the Unix timestamp for consistent filename
SET unix_timestamp = CAST(UNIX_SECONDS(CURRENT_TIMESTAMP()) AS STRING);

-- Get the most recent timestamp from our exports table. Fallback to 1990-01-01 if no records are found.
SET last_processed_timestamp = COALESCE(
  (SELECT MAX(timestamp)
   FROM `***REMOVED***.pydocs_us.exports`
   WHERE source_table = 'bigquery-public-data.pypi.distribution_metadata'),
  TIMESTAMP('1990-01-01')  -- Fallback
);

-- Create a temp table with new records
CREATE TEMP TABLE new_pypi_records AS
SELECT
  GENERATE_UUID() AS id,
  'pypi' AS ecosystem,
  name,
  version,
  description,
  home_page,
  TO_JSON_STRING(project_urls) AS project_urls,
  upload_time AS timestamp
FROM `bigquery-public-data.pypi.distribution_metadata`
WHERE upload_time > last_processed_timestamp;

-- Get count of records for export tracking
SET record_count = (SELECT COUNT(*) FROM new_pypi_records);

-- Only proceed with export if there are new records to export
IF record_count > 0 THEN
  -- Export the new records to GCS bronze zone of the datalake
  EXPORT DATA OPTIONS(
    uri=CONCAT("gs://pydocs-datalake/bronze/pypi/releases/", unix_timestamp, "-*.csv"),
    format="CSV",
    header=true,
    overwrite=true
  ) AS
  SELECT * FROM new_pypi_records;

  -- Log the export in the exports tracking table
  INSERT INTO `***REMOVED***.pydocs_us.exports`
  (id, export_name, source_table, record_count)
  VALUES (
    COALESCE((SELECT MAX(id) FROM `***REMOVED***.pydocs_us.exports`), 0) + 1,
    'pypi_releases_export',
    'bigquery-public-data.pypi.distribution_metadata',
    record_count
  );
END IF;
