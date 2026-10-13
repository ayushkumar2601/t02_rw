"""Pydantic schemas for conversation turns, state machine, and session management.

Strictly enforces allowed intents, conversation states, and payload validation.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.lead import CandidateLeadExtraction, QualificationStatus, ValidatedLead


class Intent(str, Enum):
    """Allowed intent values according to PRD specification."""

    lead_qualification = "lead_qualification"
    off_topic = "off_topic"
    human_request = "human_request"
    goodbye = "goodbye"
    unclear = "unclear"


class ConversationState(str, Enum):
    """Allowed deterministic conversation states."""

    GREETING = "GREETING"
    ASK_COMPANY = "ASK_COMPANY"
    ASK_SIZE = "ASK_SIZE"
    CLARIFY_SIZE = "CLARIFY_SIZE"
    ASK_BUDGET = "ASK_BUDGET"
    CLARIFY_BUDGET = "CLARIFY_BUDGET"
    VALIDATE_LEAD = "VALIDATE_LEAD"
    SAVE_LEAD = "SAVE_LEAD"
    CLOSING = "CLOSING"
    ENDED = "ENDED"


class SessionStatus(str, Enum):
    """Lifecycle status of a session."""

    active = "active"
    completed = "completed"
    ended = "ended"


class Speaker(str, Enum):
    """Entity speaking in a transcript turn."""

    caller = "caller"
    agent = "agent"
    system = "system"


class LLMExtractionResponse(BaseModel):
    """Raw response contract from the LLM extraction service.

    Extra fields are strictly forbidden. The backend validates and overrides
    workflow decisions where necessary.
    """

    model_config = ConfigDict(extra="forbid")

    thought_process: Optional[str] = Field(
        default=None,
        description="Chain-of-thought reasoning step before structured decision",
        max_length=2000,
    )
    intent: Intent = Field(
        default=Intent.lead_qualification,
        description="Classified intent of caller utterance",
    )
    suggested_state: Optional[ConversationState] = Field(
        default=None,
        description="Model suggested next state (untrusted)",
    )
    response: str = Field(
        description="Spoken response to deliver to the caller",
        max_length=1000,
    )
    candidate_lead: CandidateLeadExtraction = Field(
        description="Extracted candidate lead fields",
    )
    clarification_needed: Optional[str] = Field(
        default=None,
        description="Reason or question for clarification if ambiguous",
        max_length=500,
    )
    should_end_call: bool = Field(
        default=False,
        description="Whether caller explicitly indicated to end the call",
    )


class TurnRequest(BaseModel):
    """Inbound caller turn request payload."""

    model_config = ConfigDict(extra="forbid")

    turn_id: str = Field(
        min_length=1,
        max_length=128,
        description="Unique identifier for the turn to guarantee idempotency",
    )
    transcript: str = Field(
        max_length=4000,
        description="Transcribed text from the caller",
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="Client timestamp of the utterance",
    )


class TurnResponse(BaseModel):
    """Authoritative server response contract for each conversation turn."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    turn_id: str
    intent: Intent
    conversation_state: ConversationState
    state: ConversationState  # Included for backwards/cross-compatibility
    response: str
    lead: ValidatedLead
    missing_fields: List[str]
    qualification_status: QualificationStatus
    should_end_call: bool
    session_status: SessionStatus


class SessionCreateResponse(BaseModel):
    """Response returned upon creating a new session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    state: ConversationState
    status: SessionStatus
    greeting: str


class TranscriptTurnItem(BaseModel):
    """Persisted transcript turn representation."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    turn_id: str
    session_id: str
    speaker: Speaker
    text: str
    created_at: datetime


class SessionDetailResponse(BaseModel):
    """Complete session details including lead and full transcript."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    state: ConversationState
    status: SessionStatus
    lead: ValidatedLead
    missing_fields: List[str]
    qualification_status: QualificationStatus
    transcript: List[TranscriptTurnItem]
    created_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime] = None


class SessionEndResponse(BaseModel):
    """Response returned when ending or finalizing a session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    status: SessionStatus
    qualification_status: QualificationStatus
    lead_saved: bool
    lead_id: Optional[str] = None
    message: str
