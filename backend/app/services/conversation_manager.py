"""Deterministic Conversation Manager owning workflow state transitions and policy rules.

Controls the Ava SDR qualification state machine, applies retry boundaries,
enforces global transitions (goodbye, human request, off-topic, corrections),
and coordinates lead persistence.
"""

import logging
import re
from typing import Optional, Tuple
from app.config import settings
from app.models.session import Session, utc_now
from app.repositories.lead_repository import LeadRepository, lead_repository
from app.repositories.session_repository import SessionRepository, session_repository
from app.schemas.conversation import (
    ConversationState,
    Intent,
    LLMExtractionResponse,
    SessionStatus,
    Speaker,
    TurnRequest,
    TurnResponse,
)
from app.schemas.lead import BudgetPeriod, QualificationStatus, ValidatedLead
from app.services.extraction_service import ExtractionService, extraction_service
from app.services.validation_service import ValidationService, validation_service

logger = logging.getLogger("voice_agent.conversation_manager")

INITIAL_GREETING = (
    "Hello! I'm Ava, an AI assistant with the digital marketing agency. "
    "I can ask you a few quick questions to understand your business needs. Is now a good time?"
)

CLOSING_MESSAGE_SUCCESS = (
    "Thank you for sharing those details. I've recorded the information available from our conversation. "
    "Our team can review your enquiry and follow up if that option is configured. Have a great day!"
)

CLOSING_MESSAGE_FAILURE = (
    "Thank you for speaking with me. I've noted your enquiry details, though our system encountered "
    "a temporary issue saving the record. Our team will review the conversation. Have a great day!"
)


class ConversationManager:
    """State machine controller for voice agent sessions."""

    def __init__(
        self,
        session_repo: Optional[SessionRepository] = None,
        lead_repo: Optional[LeadRepository] = None,
        extraction_svc: Optional[ExtractionService] = None,
        validation_svc: Optional[ValidationService] = None,
    ):
        self.session_repo = session_repo or session_repository
        self.lead_repo = lead_repo or lead_repository
        self.extraction_svc = extraction_svc or extraction_service
        self.validation_svc = validation_svc or validation_service

    async def create_session(self, session_id: str) -> Session:
        """Initialize a new session in GREETING state."""
        session = Session(
            session_id=session_id,
            current_state=ConversationState.GREETING,
            session_status=SessionStatus.active,
            qualification_status=QualificationStatus.in_progress,
            validated_lead=ValidatedLead(),
            last_response=INITIAL_GREETING,
        )
        await self.session_repo.save_session(session)
        # Log initial greeting turn
        await self.session_repo.add_transcript_turn(
            session_id=session_id,
            turn_id=f"turn_greeting_{session_id[:8]}",
            speaker=Speaker.agent,
            text=INITIAL_GREETING,
        )
        return session

    async def process_turn(self, session_id: str, request: TurnRequest) -> TurnResponse:
        """Process an inbound utterance turn against the deterministic state machine."""
        session = await self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        # Check if session has already ended
        if session.session_status in (SessionStatus.completed, SessionStatus.ended) or session.current_state == ConversationState.ENDED:
            raise ValueError("Session has already ended. Cannot process additional turns.")

        # Check for turn idempotency
        turn_exists = await self.session_repo.has_turn(session_id, request.turn_id)
        if turn_exists:
            logger.info("Duplicate turn %s for session %s. Returning idempotent result.", request.turn_id, session_id)
            # Reconstruct and return response for the already processed turn
            missing = self.validation_svc.compute_missing_fields(session.validated_lead)
            return TurnResponse(
                session_id=session.session_id,
                turn_id=request.turn_id,
                intent=Intent.lead_qualification,
                conversation_state=session.current_state,
                state=session.current_state,
                response=session.last_response or "Understood.",
                lead=session.validated_lead,
                missing_fields=missing,
                qualification_status=session.qualification_status,
                should_end_call=(session.current_state == ConversationState.ENDED),
                session_status=session.session_status,
            )

        # 1. Log caller transcript turn
        await self.session_repo.add_transcript_turn(
            session_id=session_id,
            turn_id=request.turn_id,
            speaker=Speaker.caller,
            text=request.transcript,
            created_at=request.timestamp,
        )

        # 2. Extract facts and intent via extraction service
        missing_before = self.validation_svc.compute_missing_fields(session.validated_lead)
        extraction: LLMExtractionResponse = await self.extraction_svc.extract_candidate(
            utterance=request.transcript,
            current_state=session.current_state,
            current_lead=session.validated_lead,
            missing_fields=missing_before,
        )

        # 3. Merge candidate extractions into validated lead
        updated_lead = self.validation_svc.merge_candidate_into_validated(
            current=session.validated_lead,
            candidate=extraction.candidate_lead,
            utterance=request.transcript,
        )
        session.validated_lead = updated_lead

        # 4. Deterministic State Machine Transition
        response_text, next_state, should_end_call = await self._transition_state(
            session=session,
            extraction=extraction,
            utterance=request.transcript,
        )

        # 5. Persist lead if terminal or requested
        if next_state in (ConversationState.SAVE_LEAD, ConversationState.CLOSING, ConversationState.ENDED):
            session.qualification_status = self.validation_svc.compute_qualification_status(
                session.validated_lead,
                is_terminal=True,
                caller_declined=(extraction.intent == Intent.goodbye),
            )
            try:
                await self.lead_repo.save_lead(
                    session_id=session.session_id,
                    lead=session.validated_lead,
                    qualification_status=session.qualification_status,
                )
            except Exception as e:
                logger.error("Failed to persist lead on session end: %s", e)
                if next_state == ConversationState.SAVE_LEAD:
                    response_text = CLOSING_MESSAGE_FAILURE

            if next_state == ConversationState.SAVE_LEAD:
                next_state = ConversationState.CLOSING

        # If next state is CLOSING or caller wants to end, transition to ENDED
        if next_state == ConversationState.CLOSING or should_end_call:
            next_state = ConversationState.ENDED
            session.session_status = SessionStatus.completed
            session.ended_at = utc_now()
            should_end_call = True
        else:
            session.qualification_status = self.validation_svc.compute_qualification_status(
                session.validated_lead,
                is_terminal=False,
            )

        session.current_state = next_state
        session.last_processed_turn_id = request.turn_id
        session.last_response = response_text
        session.updated_at = utc_now()

        # Save session updates to DB
        await self.session_repo.save_session(session)

        # 6. Log agent spoken response turn
        await self.session_repo.add_transcript_turn(
            session_id=session_id,
            turn_id=f"agent_{request.turn_id}",
            speaker=Speaker.agent,
            text=response_text,
        )

        missing_after = self.validation_svc.compute_missing_fields(session.validated_lead)

        return TurnResponse(
            session_id=session.session_id,
            turn_id=request.turn_id,
            intent=extraction.intent,
            conversation_state=session.current_state,
            state=session.current_state,
            response=response_text,
            lead=session.validated_lead,
            missing_fields=missing_after,
            qualification_status=session.qualification_status,
            should_end_call=should_end_call,
            session_status=session.session_status,
        )

    async def _transition_state(
        self,
        session: Session,
        extraction: LLMExtractionResponse,
        utterance: str,
    ) -> Tuple[str, ConversationState, bool]:
        """Core deterministic state transition logic."""
        clean = utterance.strip().lower()

        # GLOBAL RULE 1: Goodbye / Caller Requests to Stop
        if extraction.intent == Intent.goodbye or extraction.should_end_call:
            return (
                "Thank you for your time. I've noted what you shared. Have a great day!",
                ConversationState.CLOSING,
                True,
            )

        # GLOBAL RULE 2: Human Representative Request
        if extraction.intent == Intent.human_request:
            pending_question = self._get_pending_question_for_state(session.current_state)
            human_msg = (
                "I am an AI assistant. Our team will review your enquiry and follow up if configured, "
                f"but I cannot transfer you to a live representative right now. {pending_question}"
            )
            return human_msg.strip(), session.current_state, False

        # GLOBAL RULE 3: Off-topic Question
        if extraction.intent == Intent.off_topic:
            pending_question = self._get_pending_question_for_state(session.current_state)
            off_topic_msg = (
                f"I focus on our digital marketing services. {pending_question}"
            )
            return off_topic_msg.strip(), session.current_state, False

        # GLOBAL RULE 4: Unclear Utterance
        if extraction.intent == Intent.unclear:
            pending_question = self._get_pending_question_for_state(session.current_state)
            unclear_msg = f"I'm sorry, I didn't quite catch that. {pending_question}"
            return unclear_msg.strip(), session.current_state, False

        # STATE-SPECIFIC TRANSITIONS
        state = session.current_state

        # Check if lead is ALREADY fully satisfied (e.g. caller gave everything in one go)
        missing = self.validation_svc.compute_missing_fields(session.validated_lead)
        if not missing:
            return CLOSING_MESSAGE_SUCCESS, ConversationState.SAVE_LEAD, True

        # State: GREETING
        if state == ConversationState.GREETING:
            decline_phrases = ["not interested", "not now", "no thanks", "don't want", "dont want", "not ready"]
            if any(p in clean for p in decline_phrases) or re.search(r"\b(no|nope)\b", clean):
                return (
                    "No problem at all. Feel free to reach out whenever you're ready. Have a great day!",
                    ConversationState.CLOSING,
                    True,
                )
            # Check if caller already mentioned company info in response to greeting
            if session.validated_lead.company_name or session.validated_lead.business_type:
                return (
                    "Thanks! Approximately how many employees or team members does your company have?",
                    ConversationState.ASK_SIZE,
                    False,
                )
            return (
                "Could you briefly tell me your company name and what your business does?",
                ConversationState.ASK_COMPANY,
                False,
            )

        # State: ASK_COMPANY
        if state == ConversationState.ASK_COMPANY:
            # Caller may decline company name: respect that
            return (
                "Thanks! Approximately how many employees or team members does your company have?",
                ConversationState.ASK_SIZE,
                False,
            )

        # State: ASK_SIZE
        if state == ConversationState.ASK_SIZE:
            if session.validated_lead.company_size is not None:
                return (
                    "Understood. Approximately how much do you spend on marketing each month?",
                    ConversationState.ASK_BUDGET,
                    False,
                )
            # Ambiguous employee count
            if session.size_clarification_count < settings.MAX_CLARIFICATION_ATTEMPTS:
                session.size_clarification_count += 1
                return (
                    "Could you give me an approximate number of employees or team members?",
                    ConversationState.CLARIFY_SIZE,
                    False,
                )
            # Max retry reached -> continue with unknown
            return (
                "No problem, we can leave that for later. Approximately how much do you spend on marketing each month?",
                ConversationState.ASK_BUDGET,
                False,
            )

        # State: CLARIFY_SIZE
        if state == ConversationState.CLARIFY_SIZE:
            # Did clarification resolve company_size?
            if session.validated_lead.company_size is not None:
                return (
                    "Understood. Approximately how much do you spend on marketing each month?",
                    ConversationState.ASK_BUDGET,
                    False,
                )
            if session.size_clarification_count < settings.MAX_CLARIFICATION_ATTEMPTS:
                session.size_clarification_count += 1
                return (
                    "Could you share roughly how many people are on your team?",
                    ConversationState.CLARIFY_SIZE,
                    False,
                )
            # Exhausted retries -> proceed
            return (
                "That's completely fine. Approximately how much do you spend on marketing each month?",
                ConversationState.ASK_BUDGET,
                False,
            )

        # State: ASK_BUDGET
        if state == ConversationState.ASK_BUDGET:
            # Check if budget is fully specified (amount + currency + period)
            b_amount = session.validated_lead.marketing_budget
            b_curr = session.validated_lead.budget_currency
            b_period = session.validated_lead.budget_period

            if b_amount is not None and b_curr and b_period != BudgetPeriod.unknown:
                return CLOSING_MESSAGE_SUCCESS, ConversationState.SAVE_LEAD, True

            # If caller explicitly doesn't know / declines
            if any(w in clean for w in ["don't know", "dont know", "not sure", "prefer not", "no idea", "skip"]):
                return CLOSING_MESSAGE_SUCCESS, ConversationState.SAVE_LEAD, True

            # Ambiguous: amount given but currency or period missing
            if session.budget_clarification_count < settings.MAX_CLARIFICATION_ATTEMPTS:
                session.budget_clarification_count += 1
                prompt = self._formulate_budget_clarification(b_amount, b_curr, b_period)
                return prompt, ConversationState.CLARIFY_BUDGET, False

            # Exhausted retries -> finish
            return CLOSING_MESSAGE_SUCCESS, ConversationState.SAVE_LEAD, True

        # State: CLARIFY_BUDGET
        if state == ConversationState.CLARIFY_BUDGET:
            b_amount = session.validated_lead.marketing_budget
            b_curr = session.validated_lead.budget_currency
            b_period = session.validated_lead.budget_period

            if b_amount is not None and b_curr and b_period != BudgetPeriod.unknown:
                return CLOSING_MESSAGE_SUCCESS, ConversationState.SAVE_LEAD, True

            if session.budget_clarification_count < settings.MAX_CLARIFICATION_ATTEMPTS:
                session.budget_clarification_count += 1
                prompt = self._formulate_budget_clarification(b_amount, b_curr, b_period)
                return prompt, ConversationState.CLARIFY_BUDGET, False

            # Exhausted retries -> finish
            return CLOSING_MESSAGE_SUCCESS, ConversationState.SAVE_LEAD, True

        # Terminal or other states
        return CLOSING_MESSAGE_SUCCESS, ConversationState.CLOSING, True

    def _get_pending_question_for_state(self, state: ConversationState) -> str:
        """Return the active qualification question for redirecting."""
        if state in (ConversationState.GREETING, ConversationState.ASK_COMPANY):
            return "Could you tell me your company name and what your business does?"
        if state in (ConversationState.ASK_SIZE, ConversationState.CLARIFY_SIZE):
            return "Approximately how many employees or team members do you have?"
        if state in (ConversationState.ASK_BUDGET, ConversationState.CLARIFY_BUDGET):
            return "Approximately how much do you spend on marketing each month?"
        return ""

    def _formulate_budget_clarification(
        self, amount: Optional[float], currency: Optional[str], period: BudgetPeriod
    ) -> str:
        """Construct focused budget clarification without re-asking established facts."""
        if amount is not None and not currency and period == BudgetPeriod.unknown:
            return "Could you specify what currency that amount is in, and whether that is monthly or annually?"
        if amount is not None and not currency:
            return "Could you specify what currency that amount is in?"
        if amount is not None and period == BudgetPeriod.unknown:
            return "Is that budget monthly, quarterly, or annually?"
        return "Could you clarify your approximate marketing budget, including currency and timeframe?"

    async def end_session(self, session_id: str) -> Tuple[Session, bool, Optional[str]]:
        """Explicitly finalize a session, save lead if needed, and close."""
        session = await self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        lead_saved = False
        lead_id: Optional[str] = None

        session.qualification_status = self.validation_svc.compute_qualification_status(
            session.validated_lead,
            is_terminal=True,
        )

        try:
            persisted = await self.lead_repo.save_lead(
                session_id=session.session_id,
                lead=session.validated_lead,
                qualification_status=session.qualification_status,
            )
            lead_saved = True
            lead_id = persisted.lead_id
        except Exception as e:
            logger.error("Failed to save lead on manual end_session: %s", e)

        session.current_state = ConversationState.ENDED
        session.session_status = SessionStatus.ended
        session.ended_at = utc_now()
        await self.session_repo.save_session(session)

        return session, lead_saved, lead_id


conversation_manager = ConversationManager()
