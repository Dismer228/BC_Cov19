from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.clients.snowflake_client import SnowflakeClient


@dataclass
class DataQueryParams:
	region_id: Optional[str]
	date_from: Optional[str]
	date_to: Optional[str]
	columns: Optional[List[str]]
	aggregate: Optional[str]
	window: int


class DataService:
	def __init__(self) -> None:
		self._sf = SnowflakeClient()

	def _rolling_mean(self, values: List[Optional[float]], window: int) -> List[Optional[float]]:
		result: List[Optional[float]] = []
		for i in range(len(values)):
			start = max(0, i - window + 1)
			slice_vals = [v for v in values[start:i + 1] if isinstance(v, (int, float))]
			if not slice_vals:
				result.append(None)
			else:
				result.append(sum(slice_vals) / len(slice_vals))
		return result

	def query_cases_by_region(self, params: DataQueryParams) -> Dict[str, Any]:
		select_cols = ["region_id", "date", "cases", "deaths", "tests"]
		if params.columns:
			allowed = set(select_cols)
			select_cols = [c for c in params.columns if c in allowed]
			if "region_id" not in select_cols:
				select_cols.insert(0, "region_id")
			if "date" not in select_cols:
				select_cols.insert(1, "date")

		where_clauses: List[str] = []
		values: List[Any] = []
		if params.region_id:
			where_clauses.append("region_id = %s")
			values.append(params.region_id)
		if params.date_from:
			where_clauses.append("date >= %s")
			values.append(params.date_from)
		if params.date_to:
			where_clauses.append("date <= %s")
			values.append(params.date_to)

		where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
		sql = f"""
			SELECT {', '.join(select_cols)}
			FROM cases_by_region
			{where_sql}
			ORDER BY region_id, date
		"""
		result = self._sf.execute(sql, params=values)

		# Convert rows to list of dicts
		rows = [dict(zip(result.columns, row)) for row in result.rows]

		if not rows:
			return {"data": [], "meta": {"rows": 0}}

		# Optional on-the-fly processing without pandas
		if params.aggregate == "rolling_mean":
			# Group by region_id
			from collections import defaultdict

			groups: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
			for r in rows:
				groups[r.get("region_id")].append(r)
			# For each group, ensure sorted by date
			for gid, records in groups.items():
				try:
					records.sort(key=lambda x: x.get("date"))
				except Exception:
					pass
				measure_cols = [c for c in records[0].keys() if c not in ("region_id", "date")]
				for col in measure_cols:
					series = [records[i].get(col) for i in range(len(records))]
					means = self._rolling_mean(series, params.window)
					for i, m in enumerate(means):
						records[i][f"{col}_{params.window}d_avg"] = m
			# Flatten back preserving global order
			rows = [rec for gid in groups for rec in groups[gid]]

		# Ensure date is serializable
		for r in rows:
			if isinstance(r.get("date"), (datetime,)):
				r["date"] = r["date"].strftime("%Y-%m-%d")

		return {"data": rows, "meta": {"rows": len(rows), "columns": list(rows[0].keys())}}