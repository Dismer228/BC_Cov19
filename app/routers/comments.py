from typing import Optional

from fastapi import APIRouter, Query

from app.models.comments import CommentCreate
from app.services.comments_service import CommentsService

router = APIRouter()


@router.get("")
async def list_comments(
    table: Optional[str] = Query(None),
    region_id: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    column: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    service = CommentsService()
    docs = await service.list_comments(
        table=table, region_id=region_id, date=date, column=column, limit=limit
    )
    return {"comments": docs, "count": len(docs)}


@router.post("")
async def create_comment(payload: CommentCreate):
    service = CommentsService()
    doc = payload.model_dump()
    doc.setdefault("status", "open")
    doc.setdefault("created_at", None)
    inserted_id = await service.create_comment(doc)
    return {"status": "created", "id": inserted_id}