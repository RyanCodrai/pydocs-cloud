-- Declare all variables at the beginning
DECLARE last_processed_timestamp TIMESTAMP;
DECLARE record_count INT64;
DECLARE unix_timestamp STRING;

-- Set the Unix timestamp for consistent filename
SET unix_timestamp = CAST(UNIX_SECONDS(CURRENT_TIMESTAMP()) AS STRING);

-- Get the most recent timestamp from our exports table. Fallback to 1990-01-01 if no records are found.
SET last_processed_timestamp = COALESCE(
  (SELECT MAX(timestamp)
   FROM `${project_id}.${dataset_id}.exports`
   WHERE source_table = 'bigquery-public-data.pypi.distribution_metadata'),
  TIMESTAMP('1990-01-01')  -- Fallback
);

-- Create a temp table with new records, grouped by package name and version
CREATE TEMP TABLE new_pypi_records AS
SELECT
  GENERATE_UUID() AS id,
  'pypi' AS ecosystem,
  name,
  version,
  -- Use ARRAY_AGG with ORDER BY to get the latest values
  ARRAY_AGG(description ORDER BY upload_time DESC LIMIT 1)[OFFSET(0)] AS description,
  ARRAY_AGG(home_page ORDER BY upload_time DESC LIMIT 1)[OFFSET(0)] AS home_page,
  ARRAY_AGG(TO_JSON_STRING(project_urls) ORDER BY upload_time DESC LIMIT 1)[OFFSET(0)] AS project_urls,
  -- Use MAX to get the latest upload_time for this package+version
  MAX(upload_time) AS timestamp
FROM `bigquery-public-data.pypi.distribution_metadata`
WHERE upload_time > last_processed_timestamp
GROUP BY name, version
ORDER BY name, version;

-- Get count of records for export tracking
SET record_count = (SELECT COUNT(*) FROM new_pypi_records);

-- Only proceed with export if there are new records to export
IF record_count > 0 THEN
  -- Export the new records to GCS releases area of the datalake
  EXPORT DATA OPTIONS(
    uri=CONCAT("gs://pydocs-datalake/releases/pypi/", unix_timestamp, "-*.csv"),
    format="CSV",
    header=true,
    overwrite=true
  ) AS
  SELECT * FROM new_pypi_records;

  -- Log the export in the exports tracking table
  INSERT INTO `${project_id}.${dataset_id}.exports`
  (id, export_name, source_table, record_count)
  VALUES (
    COALESCE((SELECT MAX(id) FROM `${project_id}.${dataset_id}.exports`), 0) + 1,
    'pypi_releases_export',
    'bigquery-public-data.pypi.distribution_metadata',
    record_count
  );
END IF;
