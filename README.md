COVID-19 Data Integration, Analysis, and Visualization Platform
==============================================================

This project integrates the Snowflake Marketplace Starschema JHU COVID-19 dataset with external demographic/economic data and automates EDA with interactive visualizations.

Stack
- Snowflake (AWS us-east-2): data warehouse and SQL analytics
- Python: data access, EDA, augmentation
- Plotly + Jinja2: interactive charts and HTML report
- World Bank API: demographic/economic enrichment (population, life expectancy, GDP per capita, hospital beds)

Prerequisites
1) Snowflake trial in AWS Ohio; subscribe to “COVID-19 Epidemiological Data (Johns Hopkins)” by Starschema
2) A local Python 3.10+ installation

Setup
1) Copy env and fill values
```
cp .env.example .env
# Fill SNOWFLAKE_* with your credentials and set role/warehouse
```

2) Create a virtual environment and install deps
```
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
If venv is unavailable in your environment, install python3-venv or run in your own machine.

Project Structure
```
src/
  utils/
    config.py               # Load Snowflake config from .env
    snowflake_client.py     # Query helpers (pandas)
  eda/
    explore_starschema.py   # Schema/table exploration and profiling
    automate_eda.py         # Automated EDA and HTML report
    templates/eda_report.html.j2
  augment/
    worldbank_ingest.py     # Fetch + load World Bank country features to Snowflake (COVID_DEV.EXT)
    create_enriched_views.py# Create enriched views joining JHU + WB
artifacts/                  # Outputs (created at runtime)
```

Quickstart
- Explore Starschema JHU dataset
```
make explore
# Outputs: artifacts/explore/* (table list, samples, column profiles)
```

- Automated EDA (global trends, top countries) and HTML report
```
make eda
# Outputs: artifacts/eda/* (interactive HTML charts) and eda_report.html
```

- Enrich with World Bank data and create Snowflake views
```
make ingest     # Loads COVID_DEV.EXT.WORLD_BANK_COUNTRY
make views      # Creates COVID_DEV.ENRICHED.* views
```

Key Snowflake Objects
- Source: `COVID19_DATA.PUBLIC.JHU_COVID_19_DAILY` (from Starschema)
- Staging: `COVID_DEV.EXT.WORLD_BANK_COUNTRY` (latest per-country indicators)
- Enriched views:
  - `COVID_DEV.ENRICHED.JHU_COUNTRY_DAILY`
  - `COVID_DEV.ENRICHED.JHU_DAILY_WITH_WB`
  - `COVID_DEV.ENRICHED.JHU_DAILY_PER_100K` (population-normalized metrics)

Automating EDA
- Run `src/eda/automate_eda.py` on a schedule (cron/GitHub Actions) to regenerate charts and `eda_report.html`.
- Parameterize time windows/countries via environment variables or CLI args.
- Persist artifacts to object storage (e.g., S3) and publish via static hosting.

Notes
- If Starschema table names differ in your region/account, first run `make explore` to list available tables, then adjust queries in `automate_eda.py`.
- World Bank indicators used: population, life expectancy, GDP per capita, hospital beds per 1k. Add more in `WB_INDICATORS` if needed.