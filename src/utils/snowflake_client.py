from __future__ import annotations

import contextlib
from typing import Iterator, Optional

import pandas as pd
import snowflake.connector

from .config import load_config


class SnowflakeClient:
    def __init__(self):
        self.cfg = load_config()

    def connect(self):
        return snowflake.connector.connect(
            account=self.cfg.account,
            user=self.cfg.user,
            password=self.cfg.password,
            role=self.cfg.role,
            warehouse=self.cfg.warehouse,
            database=self.cfg.database,
            schema=self.cfg.schema,
        )

    @contextlib.contextmanager
    def cursor(self) -> Iterator[snowflake.connector.cursor.SnowflakeCursor]:
        conn = self.connect()
        try:
            cs = conn.cursor()
            yield cs
        finally:
            with contextlib.suppress(Exception):
                cs.close()
            with contextlib.suppress(Exception):
                conn.close()

    def query_df(self, sql: str, params: Optional[dict] = None) -> pd.DataFrame:
        with self.cursor() as cs:
            cs.execute(sql, params or {})
            try:
                df = cs.fetch_pandas_all()
            except Exception:
                rows = cs.fetchall()
                cols = [c[0] for c in cs.description]
                df = pd.DataFrame(rows, columns=cols)
        return df

    def execute(self, sql: str, params: Optional[dict] = None) -> None:
        with self.cursor() as cs:
            cs.execute(sql, params or {})
