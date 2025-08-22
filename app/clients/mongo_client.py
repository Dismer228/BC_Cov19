from __future__ import annotations

from typing import Any

from app.config import get_settings


class MongoClientProvider:
	_client: Any | None = None

	@classmethod
	def get_client(cls) -> Any:
		if cls._client is None:
			settings = get_settings()
			# Lazy import to avoid hard dependency during module import
			from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore
			cls._client = AsyncIOMotorClient(settings.mongodb_uri)
		return cls._client

	@classmethod
	def get_db(cls) -> Any:
		settings = get_settings()
		return cls.get_client()[settings.mongodb_db]