from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests
from snowflake.connector import pandas_tools as sf_pandas_tools
from rich.console import Console

from src.utils.snowflake_client import SnowflakeClient


OUT = Path("artifacts/worldbank")
OUT.mkdir(parents=True, exist_ok=True)


WB_INDICATORS = {
    "SP.POP.TOTL": "population_total",
    "SP.DYN.LE00.IN": "life_expectancy",
    "NY.GDP.PCAP.CD": "gdp_per_capita_usd",
    "SH.MED.BEDS.ZS": "hospital_beds_per_1k",
}


def fetch_worldbank_indicator(indicator: str) -> pd.DataFrame:
    url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}?format=json&per_page=20000"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    data = r.json()
    rows = data[1]
    df = pd.DataFrame(rows)
    df = df[["country", "countryiso3code", "date", "value"]]
    df.rename(
        columns={"country": "country_obj", "countryiso3code": "iso3", "date": "year", "value": "value"},
        inplace=True,
    )
    df["country"] = df["country_obj"].apply(lambda x: x.get("value") if isinstance(x, dict) else x)
    df.drop(columns=["country_obj"], inplace=True)
    return df


def pivot_latest_year(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"]).sort_values(["iso3", "year"]).groupby("iso3").tail(1)
    df = df[["iso3", "country", "value"]].rename(columns={"value": column_name})
    return df


def build_worldbank_wide() -> pd.DataFrame:
    frames = []
    for ind, col in WB_INDICATORS.items():
        df = fetch_worldbank_indicator(ind)
        df = pivot_latest_year(df, col)
        frames.append(df)
    wide = frames[0]
    for f in frames[1:]:
        wide = pd.merge(wide, f.drop(columns=["country"]), on="iso3", how="outer")
    return wide


def ensure_ext_schema(client: SnowflakeClient):
    client.execute("CREATE DATABASE IF NOT EXISTS COVID_DEV")
    client.execute("CREATE SCHEMA IF NOT EXISTS COVID_DEV.EXT")
    client.execute("CREATE SCHEMA IF NOT EXISTS COVID_DEV.ENRICHED")


def load_dataframe_to_snowflake(client: SnowflakeClient, df: pd.DataFrame, table: str):
    # Use a transient table for development safety
    create_sql = f"""
        CREATE OR REPLACE TRANSIENT TABLE COVID_DEV.EXT.{table} AS
        SELECT * FROM VALUES (1) AS T(dummy);
    """
    client.execute(create_sql)
    # Replace with pandas write via write_pandas for simplicity
    with client.connect() as conn:
        success, nchunks, nrows, _ = sf_pandas_tools.write_pandas(
            conn, df, table_name=table, database="COVID_DEV", schema="EXT", auto_create_table=True, overwrite=True
        )
        if not success:
            raise RuntimeError("write_pandas failed")


def main():
    console = Console()
    console.log("Fetching World Bank indicators...")
    wide = build_worldbank_wide()
    OUT.joinpath("worldbank_wide.csv").write_text(wide.to_csv(index=False))
    console.log(f"Saved {len(wide)} rows to {OUT}")

    client = SnowflakeClient()
    ensure_ext_schema(client)

    # Load into Snowflake as COVID_DEV.EXT.WORLD_BANK_COUNTRY
    console.log("Loading World Bank data into Snowflake (COVID_DEV.EXT.WORLD_BANK_COUNTRY)...")
    load_dataframe_to_snowflake(client, wide, table="WORLD_BANK_COUNTRY")
    console.log("World Bank data loaded.")


if __name__ == "__main__":
    main()
