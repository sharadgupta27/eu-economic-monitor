{{ config(materialized='table') }}

SELECT
    g.country_code,
    g.country_name,
    g.reference_year,
    g.reference_date,
    g.gdp_meur,
    g.gdp_beur,
    u.unemployment_rate,
    e.energy_intensity,
    i.inflation_rate
FROM {{ ref('stg_gdp') }} g
LEFT JOIN {{ ref('stg_unemployment') }} u
    ON g.country_code = u.country_code
   AND g.reference_year = u.reference_year
LEFT JOIN {{ ref('stg_energy') }} e
    ON g.country_code = e.country_code
   AND g.reference_year = e.reference_year
LEFT JOIN {{ ref('stg_inflation') }} i
    ON g.country_code = i.country_code
   AND g.reference_year = i.reference_year
