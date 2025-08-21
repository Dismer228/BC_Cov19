from __future__ import annotations

from rich.console import Console

from src.utils.snowflake_client import SnowflakeClient


CREATE_VIEWS_SQL = """
CREATE DATABASE IF NOT EXISTS COVID_DEV;
CREATE SCHEMA IF NOT EXISTS COVID_DEV.ENRICHED;

-- Normalized country mapping for JHU names to ISO3 using World Bank names as canonical
CREATE OR REPLACE VIEW COVID_DEV.ENRICHED.JHU_COUNTRY_DAILY AS
WITH base AS (
    SELECT
        UPPER(TRIM(COALESCE(COUNTRY_REGION, COUNTRY))) AS country_key,
        COALESCE(COUNTRY_REGION, COUNTRY) AS country_name,
        DATE::DATE AS date,
        SUM(NEW_CONFIRMED) AS new_cases,
        SUM(NEW_DEATHS) AS new_deaths,
        SUM(CUMULATIVE_CONFIRMED) AS cum_cases,
        SUM(CUMULATIVE_DEATHS) AS cum_deaths
    FROM COVID19_DATA.PUBLIC.JHU_COVID_19_DAILY
    GROUP BY 1,2,3
)
SELECT * FROM base;

-- Join with World Bank country features using country name equality (approximate)
CREATE OR REPLACE VIEW COVID_DEV.ENRICHED.JHU_DAILY_WITH_WB AS
SELECT
    j.country_name,
    j.date,
    j.new_cases,
    j.new_deaths,
    j.cum_cases,
    j.cum_deaths,
    wb.iso3,
    wb.population_total,
    wb.life_expectancy,
    wb.gdp_per_capita_usd,
    wb.hospital_beds_per_1k
FROM COVID_DEV.ENRICHED.JHU_COUNTRY_DAILY j
LEFT JOIN (
    SELECT UPPER(TRIM(country)) AS country_key, *
    FROM COVID_DEV.EXT.WORLD_BANK_COUNTRY
) wb
ON j.country_key = wb.country_key;

-- Convenience view: per-100k metrics
CREATE OR REPLACE VIEW COVID_DEV.ENRICHED.JHU_DAILY_PER_100K AS
SELECT
    country_name,
    date,
    new_cases,
    new_deaths,
    cum_cases,
    cum_deaths,
    population_total,
    CASE WHEN population_total > 0 THEN (new_cases / population_total) * 100000 ELSE NULL END AS new_cases_per_100k,
    CASE WHEN population_total > 0 THEN (new_deaths / population_total) * 100000 ELSE NULL END AS new_deaths_per_100k,
    CASE WHEN population_total > 0 THEN (cum_cases / population_total) * 100000 ELSE NULL END AS cum_cases_per_100k,
    CASE WHEN population_total > 0 THEN (cum_deaths / population_total) * 100000 ELSE NULL END AS cum_deaths_per_100k,
    iso3,
    life_expectancy,
    gdp_per_capita_usd,
    hospital_beds_per_1k
FROM COVID_DEV.ENRICHED.JHU_DAILY_WITH_WB;
"""


def main():
    console = Console()
    client = SnowflakeClient()
    console.log("Creating enriched views in Snowflake...")
    for stmt in [s for s in CREATE_VIEWS_SQL.split(";\n") if s.strip()]:
        client.execute(stmt)
    console.log("Enriched views created under COVID_DEV.ENRICHED")


if __name__ == "__main__":
    main()
