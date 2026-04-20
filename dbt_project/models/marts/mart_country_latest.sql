{{ config(
    materialized='table',
    partition_by=none,
    cluster_by=['country_code']
) }}

/*
  Latest available snapshot for each country — used for KPI cards
  and the EU choropleth map on the dashboard home page.
*/
WITH latest_year AS (
    SELECT
        country_code,
        MAX(reference_year) AS latest_year
    FROM {{ ref('int_country_indicators') }}
    WHERE gdp_meur IS NOT NULL
    GROUP BY country_code
)

SELECT
    i.country_code,
    i.country_name,
    i.reference_year                        AS latest_year,
    ROUND(i.gdp_beur, 2)                    AS gdp_beur,
    ROUND(i.unemployment_rate, 2)           AS unemployment_rate,
    ROUND(i.energy_intensity, 3)            AS energy_intensity,
    ROUND(i.inflation_rate, 2)              AS inflation_rate,
    ROUND(d.gdp_yoy_growth_pct, 2)          AS gdp_yoy_growth_pct,
    ROUND(d.unem_yoy_change, 2)             AS unem_yoy_change,
    ROUND(c.composite_score, 1)             AS composite_score,
    ROUND(c.gdp_score, 1)                   AS gdp_score,
    ROUND(c.unemployment_score, 1)          AS unemployment_score,
    ROUND(c.energy_score, 1)               AS energy_score
FROM {{ ref('int_country_indicators') }} i
JOIN latest_year ly
    ON i.country_code = ly.country_code
   AND i.reference_year = ly.latest_year
LEFT JOIN {{ ref('int_yoy_deltas') }} d
    ON i.country_code = d.country_code
   AND i.reference_year = d.reference_year
LEFT JOIN {{ ref('mart_composite_economic_index') }} c
    ON i.country_code = c.country_code
   AND i.reference_year = c.reference_year
QUALIFY ROW_NUMBER() OVER (PARTITION BY i.country_code ORDER BY i.reference_year DESC) = 1
