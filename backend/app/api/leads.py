"""API endpoints for querying persisted lead records."""

from typing import List
from fastapi import APIRouter, HTTPException, Query, status

from app.repositories.lead_repository import lead_repository
from app.schemas.lead import PersistedLeadRecord

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("", response_model=List[PersistedLeadRecord])
async def list_leads(
    limit: int = Query(default=50, ge=1, le=100, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Records offset"),
) -> List[PersistedLeadRecord]:
    """Retrieve persisted leads in reverse chronological order."""
    return await lead_repository.list_leads(limit=limit, offset=offset)


@router.get("/{lead_id}", response_model=PersistedLeadRecord)
async def get_lead(lead_id: str) -> PersistedLeadRecord:
    """Retrieve a single persisted lead by its unique lead_id."""
    lead = await lead_repository.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead '{lead_id}' not found.",
        )
    return lead
