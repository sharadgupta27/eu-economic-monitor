{{ config(materialized='table') }}

WITH lagged AS (
    SELECT
        country_code,
        country_name,
        reference_year,
        reference_date,
        gdp_meur,
        gdp_beur,
        unemployment_rate,
        energy_intensity,
        inflation_rate,

        -- Previous year values
        LAG(gdp_meur)           OVER w AS prev_gdp_meur,
        LAG(unemployment_rate)  OVER w AS prev_unemployment,
        LAG(energy_intensity)   OVER w AS prev_energy,
        LAG(inflation_rate)     OVER w AS prev_inflation
    FROM {{ ref('int_country_indicators') }}
    WINDOW w AS (PARTITION BY country_code ORDER BY reference_year)
)

SELECT
    country_code,
    country_name,
    reference_year,
    reference_date,
    gdp_meur,
    gdp_beur,

    -- GDP YoY
    ROUND(gdp_meur - prev_gdp_meur, 2)                                              AS gdp_yoy_change_meur,
    ROUND(
        SAFE_DIVIDE(gdp_meur - prev_gdp_meur, NULLIF(prev_gdp_meur, 0)) * 100,
        2
    )                                                                               AS gdp_yoy_growth_pct,

    unemployment_rate,
    ROUND(unemployment_rate - prev_unemployment, 2)                                 AS unem_yoy_change,

    energy_intensity,
    ROUND(energy_intensity - prev_energy, 3)                                        AS energy_yoy_change,
    ROUND(
        SAFE_DIVIDE(prev_energy - energy_intensity, NULLIF(prev_energy, 0)) * 100,
        2
    )                                                                               AS energy_yoy_improvement_pct,

    inflation_rate,
    ROUND(inflation_rate - prev_inflation, 2)                                       AS inflation_yoy_change

FROM lagged
