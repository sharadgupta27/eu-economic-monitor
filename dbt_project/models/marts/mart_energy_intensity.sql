{{ config(
    materialized='table',
    partition_by={'field': 'reference_date', 'data_type': 'date', 'granularity': 'year'},
    cluster_by=['country_code']
) }}

SELECT
    country_code,
    country_name,
    reference_year,
    reference_date,
    ROUND(energy_intensity, 3)          AS energy_intensity,
    ROUND(energy_yoy_change, 3)         AS energy_yoy_change,
    ROUND(energy_yoy_improvement_pct, 2) AS energy_yoy_improvement_pct
FROM {{ ref('int_yoy_deltas') }}
WHERE energy_intensity IS NOT NULL

