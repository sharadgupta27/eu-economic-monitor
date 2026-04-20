{{ config(materialized='view') }}

SELECT
    TRIM(country_code)                        AS country_code,
    TRIM(country_name)                        AS country_name,
    CAST(year AS INT64)                       AS reference_year,
    DATE(CAST(year AS INT64), 1, 1)           AS reference_date,
    CAST(value AS FLOAT64)                    AS gdp_meur,
    ROUND(CAST(value AS FLOAT64) / 1000, 3)   AS gdp_beur,
    unit,
    loaded_at
FROM {{ source('eurostat_raw', 'gdp_annual') }}
WHERE value IS NOT NULL
  AND year IS NOT NULL
  AND country_code IS NOT NULL
  AND CAST(year AS INT64) BETWEEN 2000 AND 2030
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY TRIM(country_code), CAST(year AS INT64)
    ORDER BY loaded_at DESC
) = 1
