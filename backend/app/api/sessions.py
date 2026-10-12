"""API endpoints for session lifecycle, turn processing, and transcript retrieval."""

import uuid
from fastapi import APIRouter, HTTPException, status

from app.models.session import Session
from app.repositories.lead_repository import lead_repository
from app.repositories.session_repository import session_repository
from app.schemas.conversation import (
    SessionCreateResponse,
    SessionDetailResponse,
    SessionEndResponse,
    TurnRequest,
    TurnResponse,
)
from app.services.conversation_manager import INITIAL_GREETING, conversation_manager
from app.services.validation_service import validation_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session() -> SessionCreateResponse:
    """Create a new voice session and initialize conversation state."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    session: Session = await conversation_manager.create_session(session_id)

    return SessionCreateResponse(
        session_id=session.session_id,
        state=session.current_state,
        status=session.session_status,
        greeting=INITIAL_GREETING,
    )


@router.post("/{session_id}/turns", response_model=TurnResponse)
async def process_turn(session_id: str, request: TurnRequest) -> TurnResponse:
    """Process an incoming caller utterance turn."""
    # Validate payload length limits
    if not request.turn_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="turn_id cannot be blank.",
        )
    if len(request.transcript) > 4000:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Transcript exceeds maximum allowed length of 4000 characters.",
        )

    try:
        response = await conversation_manager.process_turn(session_id, request)
        return response
    except ValueError as exc:
        err_msg = str(exc)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        if "already ended" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str) -> SessionDetailResponse:
    """Retrieve full session state, validated lead data, and complete transcript."""
    session = await session_repository.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    # If lead was persisted, load saved lead details
    persisted = await lead_repository.get_lead_by_session_id(session_id)
    lead_data = session.validated_lead
    if persisted:
        lead_data = lead_data.model_copy(
            update={
                "company_name": persisted.company_name,
                "business_type": persisted.business_type,
                "company_size": persisted.company_size,
                "marketing_budget": persisted.marketing_budget,
                "budget_currency": persisted.budget_currency,
                "budget_period": persisted.budget_period,
                "contact_name": persisted.contact_name,
                "contact_email": persisted.contact_email,
            }
        )

    transcript = await session_repository.get_transcript(session_id)
    missing = validation_service.compute_missing_fields(lead_data)

    return SessionDetailResponse(
        session_id=session.session_id,
        state=session.current_state,
        status=session.session_status,
        lead=lead_data,
        missing_fields=missing,
        qualification_status=session.qualification_status,
        transcript=transcript,
        created_at=session.created_at,
        updated_at=session.updated_at,
        ended_at=session.ended_at,
    )


@router.post("/{session_id}/end", response_model=SessionEndResponse)
async def end_session(session_id: str) -> SessionEndResponse:
    """Finalize a session, store available lead data, and close."""
    try:
        session, lead_saved, lead_id = await conversation_manager.end_session(session_id)
        msg = "Session completed and lead persisted." if lead_saved else "Session completed without lead persistence."
        return SessionEndResponse(
            session_id=session.session_id,
            status=session.session_status,
            qualification_status=session.qualification_status,
            lead_saved=lead_saved,
            lead_id=lead_id,
            message=msg,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
