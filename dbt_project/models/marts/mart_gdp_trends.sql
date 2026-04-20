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
    ROUND(gdp_beur, 3)             AS gdp_beur,
    ROUND(gdp_meur, 0)             AS gdp_meur,
    gdp_yoy_change_meur,
    gdp_yoy_growth_pct
FROM {{ ref('int_yoy_deltas') }}
WHERE gdp_meur IS NOT NULL

