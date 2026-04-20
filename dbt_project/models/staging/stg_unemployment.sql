{{ config(materialized='view') }}

SELECT
    TRIM(country_code)              AS country_code,
    TRIM(country_name)              AS country_name,
    CAST(year AS INT64)             AS reference_year,
    DATE(CAST(year AS INT64), 1, 1) AS reference_date,
    CAST(value AS FLOAT64)          AS unemployment_rate,
    unit,
    age_group,
    sex,
    loaded_at
FROM {{ source('eurostat_raw', 'unemployment_annual') }}
WHERE value IS NOT NULL
  AND year IS NOT NULL
  AND country_code IS NOT NULL
  AND age_group = 'Y15-74'
  AND sex = 'T'
  AND CAST(year AS INT64) BETWEEN 2000 AND 2030
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY TRIM(country_code), CAST(year AS INT64)
    ORDER BY loaded_at DESC
) = 1
