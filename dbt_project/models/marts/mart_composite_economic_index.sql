{{ config(
    materialized='table',
    partition_by={'field': 'reference_date', 'data_type': 'date', 'granularity': 'year'},
    cluster_by=['country_code']
) }}

/*
  Composite Economic Index (0–100):
    - GDP score       : higher YoY growth → higher score
    - Unemployment    : lower rate         → higher score (inverted)
    - Energy score    : lower intensity    → higher score (inverted)
  Each sub-score is min-max normalised within each year globally.
  Final composite = simple average of the three sub-scores.
*/
WITH raw AS (
    SELECT
        country_code,
        country_name,
        reference_year,
        reference_date,
        gdp_yoy_growth_pct,
        unemployment_rate,
        energy_intensity,

        -- Annual min/max for normalisation
        MIN(gdp_yoy_growth_pct)  OVER (PARTITION BY reference_year) AS min_gdp_growth,
        MAX(gdp_yoy_growth_pct)  OVER (PARTITION BY reference_year) AS max_gdp_growth,
        MIN(unemployment_rate)   OVER (PARTITION BY reference_year) AS min_unem,
        MAX(unemployment_rate)   OVER (PARTITION BY reference_year) AS max_unem,
        MIN(energy_intensity)    OVER (PARTITION BY reference_year) AS min_energy,
        MAX(energy_intensity)    OVER (PARTITION BY reference_year) AS max_energy
    FROM {{ ref('int_yoy_deltas') }}
    WHERE reference_year >= 2000
),

scored AS (
    SELECT
        country_code,
        country_name,
        reference_year,
        reference_date,

        ROUND(
            100 * SAFE_DIVIDE(
                gdp_yoy_growth_pct - min_gdp_growth,
                NULLIF(max_gdp_growth - min_gdp_growth, 0)
            ), 1
        ) AS gdp_score,

        ROUND(
            100 * (1 - SAFE_DIVIDE(
                unemployment_rate - min_unem,
                NULLIF(max_unem - min_unem, 0)
            )), 1
        ) AS unemployment_score,

        ROUND(
            100 * (1 - SAFE_DIVIDE(
                energy_intensity - min_energy,
                NULLIF(max_energy - min_energy, 0)
            )), 1
        ) AS energy_score

    FROM raw
)

SELECT
    country_code,
    country_name,
    reference_year,
    reference_date,
    COALESCE(gdp_score, 50)          AS gdp_score,
    COALESCE(unemployment_score, 50) AS unemployment_score,
    COALESCE(energy_score, 50)       AS energy_score,
    ROUND(
        (COALESCE(gdp_score, 50) + COALESCE(unemployment_score, 50) + COALESCE(energy_score, 50)) / 3,
        1
    )                                AS composite_score
FROM scored
