"""In-memory domain model for active voice agent sessions.

Tracks ongoing state machine metadata, clarification retry counts,
and turn idempotency before and alongside database persistence.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.conversation import ConversationState, SessionStatus
from app.schemas.lead import QualificationStatus, ValidatedLead


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class Session(BaseModel):
    """Domain model representing an active or completed session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    current_state: ConversationState = ConversationState.GREETING
    session_status: SessionStatus = SessionStatus.active
    qualification_status: QualificationStatus = QualificationStatus.in_progress
    validated_lead: ValidatedLead = Field(default_factory=ValidatedLead)
    size_clarification_count: int = 0
    budget_clarification_count: int = 0
    last_processed_turn_id: Optional[str] = None
    last_response: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    ended_at: Optional[datetime] = None
