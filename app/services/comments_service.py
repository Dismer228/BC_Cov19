from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.clients.mongo_client import MongoClientProvider


class CommentsService:
	def __init__(self) -> None:
		self._db = MongoClientProvider.get_db()

	def _normalize_id(self, doc: Dict[str, Any]) -> Dict[str, Any]:
		if not doc:
			return doc
		doc["_id"] = str(doc.get("_id"))
		return doc

	async def list_comments(
		self,
		table: Optional[str] = None,
		region_id: Optional[str] = None,
		date: Optional[str] = None,
		column: Optional[str] = None,
		limit: int = 100,
	) -> List[Dict[str, Any]]:
		query: Dict[str, Any] = {}
		if table:
			query["target.table"] = table
		if column:
			query["target.column"] = column
		if region_id:
			query["target.row_locator.region_id"] = region_id
		if date:
			try:
				query["target.row_locator.date"] = datetime.fromisoformat(date)
			except Exception:
				query["target.row_locator.date"] = date

		cursor = self._db["comments"].find(query).sort("created_at", -1).limit(limit)
		docs = [self._normalize_id(d) async for d in cursor]
		return docs

	async def create_comment(self, payload: Dict[str, Any]) -> str:
		payload.setdefault("status", "open")
		payload.setdefault("created_at", datetime.utcnow())
		res = await self._db["comments"].insert_one(payload)
		return str(res.inserted_id)