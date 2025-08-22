from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from app.config import get_settings


@dataclass
class SnowflakeQueryResult:
	columns: list[str]
	rows: list[tuple[Any, ...]]


class SnowflakeClient:
	def __init__(self) -> None:
		self._settings = get_settings()
		self._conn = None

	def connect(self) -> Any:
		# Lazy import to avoid hard dependency at import time
		import snowflake.connector  # type: ignore

		if self._conn is None or getattr(self._conn, "is_closed", lambda: True)():
			self._conn = snowflake.connector.connect(
				account=self._settings.snowflake_account,
				user=self._settings.snowflake_user,
				password=self._settings.snowflake_password,
				warehouse=self._settings.snowflake_warehouse,
				database=self._settings.snowflake_database,
				schema=self._settings.snowflake_schema,
				role=self._settings.snowflake_role,
			)
		return self._conn

	def close(self) -> None:
		if self._conn is not None:
			with contextlib.suppress(Exception):
				self._conn.close()
			self._conn = None

	def execute(self, sql: str, params: Optional[Iterable[Any]] = None) -> SnowflakeQueryResult:
		conn = self.connect()
		cursor = conn.cursor()
		try:
			cursor.execute(sql, params=params)
			cols = [d[0] for d in cursor.description] if cursor.description else []
			rows = cursor.fetchall() if cursor.description else []
			return SnowflakeQueryResult(columns=cols, rows=rows)
		finally:
			cursor.close()