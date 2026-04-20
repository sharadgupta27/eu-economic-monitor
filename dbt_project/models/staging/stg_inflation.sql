{{ config(materialized='view') }}

SELECT
    TRIM(country_code)              AS country_code,
    TRIM(country_name)              AS country_name,
    CAST(year AS INT64)             AS reference_year,
    DATE(CAST(year AS INT64), 1, 1) AS reference_date,
    CAST(value AS FLOAT64)          AS inflation_rate,
    unit,
    loaded_at
FROM {{ source('eurostat_raw', 'inflation_annual') }}
WHERE value IS NOT NULL
  AND year IS NOT NULL
  AND country_code IS NOT NULL
  AND CAST(year AS INT64) BETWEEN 2000 AND 2030
