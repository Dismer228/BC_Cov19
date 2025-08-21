from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from rich import print
from rich.console import Console
from rich.table import Table

from src.utils.snowflake_client import SnowflakeClient


OUTPUT_DIR = Path("artifacts/explore")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def show_tables(client: SnowflakeClient) -> List[Dict]:
    df = client.query_df(
        """
        SELECT TABLE_SCHEMA, TABLE_NAME, ROW_COUNT, BYTES
        FROM COVID19_DATA.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
    )
    tables = df.to_dict(orient="records")
    (OUTPUT_DIR / "tables.json").write_text(json.dumps(tables, indent=2))
    return tables


def sample_table(client: SnowflakeClient, schema: str, table: str, limit: int = 10):
    df = client.query_df(f"SELECT * FROM COVID19_DATA.{schema}.{table} LIMIT {limit}")
    df.to_csv(OUTPUT_DIR / f"sample_{schema}_{table}.csv", index=False)
    return df


def profile_columns(client: SnowflakeClient, schema: str, table: str):
    df = client.query_df(
        f"""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COMMENT
        FROM COVID19_DATA.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %%(schema)s AND TABLE_NAME = %%(table)s
        ORDER BY ORDINAL_POSITION
        """,
        {"schema": schema, "table": table},
    )
    df.to_csv(OUTPUT_DIR / f"columns_{schema}_{table}.csv", index=False)
    return df


def main():
    console = Console()
    client = SnowflakeClient()

    console.log("Listing tables in Starschema JHU dataset...")
    tables = show_tables(client)

    table = Table(title="COVID19_DATA Tables")
    table.add_column("Schema")
    table.add_column("Table")
    table.add_column("Rows")
    table.add_column("Bytes")
    for t in tables:
        table.add_row(
            str(t["TABLE_SCHEMA"]),
            str(t["TABLE_NAME"]),
            str(t.get("ROW_COUNT", "")),
            str(t.get("BYTES", "")),
        )
    console.print(table)

    # Heuristic: explore top likely tables
    candidates = [
        ("PUBLIC", "JHU_COVID_19"),
        ("PUBLIC", "JHU_COVID_19_DAILY"),
        ("PUBLIC", "JHU_COVID_19_GLOBAL"),
    ]
    discovered = {(t["TABLE_SCHEMA"], t["TABLE_NAME"]) for t in tables}
    for schema, name in candidates:
        if (schema, name) in discovered:
            console.log(f"Profiling {schema}.{name} ...")
            profile_columns(client, schema, name)
            sample_table(client, schema, name, limit=25)

    console.log(f"Artifacts written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
