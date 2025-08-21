from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict

import pandas as pd
import plotly.express as px
from jinja2 import Environment, FileSystemLoader, select_autoescape
from rich.console import Console

from src.utils.snowflake_client import SnowflakeClient


ARTIFACTS = Path("artifacts/eda")
ARTIFACTS.mkdir(parents=True, exist_ok=True)
TEMPLATES = Path("src/eda/templates")


def resolve_jhu_daily_table(client: SnowflakeClient) -> str:
    candidates = (
        "JHU_COVID_19_DAILY",
        "COVID_19_DAILY",
        "EPIDEMIOLOGY_DAILY",
        "JHU_COVID_19",
    )
    df = client.query_df(
        """
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE UPPER(TABLE_NAME) IN (%s,%s,%s,%s)
        ORDER BY CASE WHEN UPPER(TABLE_NAME) LIKE '%DAILY%' THEN 0 ELSE 1 END, TABLE_NAME
        """,
        tuple(candidates),
    )
    if df.empty:
        raise RuntimeError("Could not locate JHU daily table in current database; run explore first.")
    row = df.iloc[0]
    return f"{row['TABLE_SCHEMA']}.{row['TABLE_NAME']}"


def fetch_daily_timeseries(client: SnowflakeClient) -> pd.DataFrame:
    full_table = resolve_jhu_daily_table(client)
    sql = f"""
        WITH base AS (
            SELECT
                COALESCE(COUNTRY_REGION, COUNTRY) AS country,
                DATE::DATE AS date,
                SUM(NEW_CONFIRMED) AS new_cases,
                SUM(NEW_DEATHS) AS new_deaths,
                SUM(CUMULATIVE_CONFIRMED) AS cum_cases,
                SUM(CUMULATIVE_DEATHS) AS cum_deaths
            FROM {full_table}
            GROUP BY 1,2
        )
        SELECT * FROM base
    """
    return client.query_df(sql)


def country_latest_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.groupby("country")["date"].transform("max") == df["date"]
    latest = df[idx].sort_values("cum_cases", ascending=False)
    return latest


def plot_global_trends(df: pd.DataFrame) -> Dict[str, str]:
    outputs: Dict[str, str] = {}
    daily_global = df.groupby("date").sum(numeric_only=True).reset_index()
    fig_cases = px.line(daily_global, x="date", y="new_cases", title="Global New Cases")
    fig_deaths = px.line(daily_global, x="date", y="new_deaths", title="Global New Deaths")
    fig_cum_cases = px.line(daily_global, x="date", y="cum_cases", title="Global Cumulative Cases")
    fig_cum_deaths = px.line(daily_global, x="date", y="cum_deaths", title="Global Cumulative Deaths")

    for name, fig in {
        "global_new_cases": fig_cases,
        "global_new_deaths": fig_deaths,
        "global_cum_cases": fig_cum_cases,
        "global_cum_deaths": fig_cum_deaths,
    }.items():
        out = ARTIFACTS / f"{name}.html"
        fig.write_html(out)
        outputs[name] = str(out)
    return outputs


def plot_top_countries(df: pd.DataFrame, n: int = 10) -> Dict[str, str]:
    outputs: Dict[str, str] = {}
    latest = country_latest_snapshot(df).head(n)
    fig_bar = px.bar(latest, x="country", y="cum_cases", title=f"Top {n} Countries by Cumulative Cases")
    out = ARTIFACTS / "top_countries_cum_cases.html"
    fig_bar.write_html(out)
    outputs["top_countries_cum_cases"] = str(out)
    return outputs


def render_report(context: Dict):
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("eda_report.html.j2")
    html = template.render(**context)
    out = ARTIFACTS / "eda_report.html"
    out.write_text(html)
    return out


def main():
    console = Console()
    client = SnowflakeClient()
    console.log("Fetching daily time series from Snowflake...")
    df = fetch_daily_timeseries(client)

    console.log("Generating global trend plots...")
    trends = plot_global_trends(df)
    top = plot_top_countries(df, n=15)

    meta = {
        "generated_on": date.today().isoformat(),
        "rows": int(len(df)),
        "countries": int(df["country"].nunique()),
        "date_min": str(df["date"].min()),
        "date_max": str(df["date"].max()),
    }
    (ARTIFACTS / "summary.json").write_text(json.dumps(meta, indent=2))

    console.log("Rendering EDA report...")
    report = render_report({
        "meta": meta,
        "charts": {**trends, **top},
    })
    console.log(f"EDA artifacts saved to {ARTIFACTS}; open {report}")


if __name__ == "__main__":
    main()
