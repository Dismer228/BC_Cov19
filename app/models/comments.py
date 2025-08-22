from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Target(BaseModel):
	warehouse: str = Field(default="snowflake")
	database: str
	schema: str
	table: str
	row_pk_hash: Optional[str] = None
	row_locator: Optional[dict] = None
	column: Optional[str] = None


class CommentCreate(BaseModel):
	target: Target
	body: str
	tags: List[str] = Field(default_factory=list)
	mentions: List[str] = Field(default_factory=list)


class CommentOut(BaseModel):
	id: str = Field(alias="_id")
	target: Target
	body: str
	tags: List[str] = Field(default_factory=list)
	mentions: List[str] = Field(default_factory=list)
	status: str = "open"

	class Config:
		populate_by_name = True