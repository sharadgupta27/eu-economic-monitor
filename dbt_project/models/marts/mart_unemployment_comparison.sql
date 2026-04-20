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
    ROUND(unemployment_rate, 2)  AS unemployment_rate,
    ROUND(unem_yoy_change, 2)    AS unem_yoy_change
FROM {{ ref('int_yoy_deltas') }}
WHERE unemployment_rate IS NOT NULL

