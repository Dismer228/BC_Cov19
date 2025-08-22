from typing import List, Optional

from fastapi import APIRouter, Query

from app.services.data_service import DataQueryParams, DataService

router = APIRouter()


@router.get("/cases_by_region")
async def get_cases_by_region(
    region_id: Optional[str] = None,
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    columns: Optional[List[str]] = Query(None, description="Fields to include"),
    aggregate: Optional[str] = Query(None, description="e.g., rolling_mean"),
    window: int = Query(7, ge=1, le=365, description="Window size for rolling aggregation"),
):
    service = DataService()
    params = DataQueryParams(
        region_id=region_id,
        date_from=date_from,
        date_to=date_to,
        columns=columns,
        aggregate=aggregate,
        window=window,
    )
    result = service.query_cases_by_region(params)
    return result