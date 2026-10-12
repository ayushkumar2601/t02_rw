"""Tests for the deterministic state machine transitions, global policies, and edge cases."""

import pytest

from app.schemas.conversation import ConversationState, Intent, SessionStatus, TurnRequest
from app.schemas.lead import BudgetPeriod, QualificationStatus


@pytest.mark.asyncio
async def test_normal_qualification_workflow(conv_manager, lead_repo):
    """Test full multi-turn happy path leading to qualified lead."""
    session = await conv_manager.create_session("sess_happy_path")
    assert session.current_state == ConversationState.GREETING

    # Turn 1: Caller agrees to chat
    t1 = await conv_manager.process_turn(
        "sess_happy_path",
        TurnRequest(turn_id="turn_1", transcript="Yes, now is a great time."),
    )
    assert t1.conversation_state == ConversationState.ASK_COMPANY
    assert "company name" in t1.response.lower()

    # Turn 2: Company details provided
    t2 = await conv_manager.process_turn(
        "sess_happy_path",
        TurnRequest(turn_id="turn_2", transcript="We are Acme Digital and we do e-commerce."),
    )
    assert t2.conversation_state == ConversationState.ASK_SIZE
    assert t2.lead.company_name == "Acme Digital"
    assert t2.lead.business_type == "E-commerce"

    # Turn 3: Company size provided
    t3 = await conv_manager.process_turn(
        "sess_happy_path",
        TurnRequest(turn_id="turn_3", transcript="We have twenty-five employees."),
    )
    assert t3.conversation_state == ConversationState.ASK_BUDGET
    assert t3.lead.company_size == 25

    # Turn 4: Budget provided with currency and period
    t4 = await conv_manager.process_turn(
        "sess_happy_path",
        TurnRequest(turn_id="turn_4", transcript="We spend ₹50,000 per month on marketing."),
    )
    # Reaches terminal state
    assert t4.conversation_state == ConversationState.ENDED
    assert t4.should_end_call is True
    assert t4.qualification_status == QualificationStatus.qualified
    assert t4.lead.marketing_budget == 50000.0
    assert t4.lead.budget_currency == "INR"
    assert t4.lead.budget_period == BudgetPeriod.monthly

    # Verify lead was persisted in database
    persisted = await lead_repo.get_lead_by_session_id("sess_happy_path")
    assert persisted is not None
    assert persisted.qualification_status == QualificationStatus.qualified
    assert persisted.company_name == "Acme Digital"
    assert persisted.company_size == 25


@pytest.mark.asyncio
async def test_caller_declines_at_greeting(conv_manager):
    """Test caller declining at the greeting step."""
    session = await conv_manager.create_session("sess_decline")
    t1 = await conv_manager.process_turn(
        "sess_decline",
        TurnRequest(turn_id="t1", transcript="No, I'm not interested right now."),
    )
    assert t1.conversation_state == ConversationState.ENDED
    assert t1.should_end_call is True
    # Caller declining should be partially_qualified (not disqualified per PRD rules)
    assert t1.qualification_status == QualificationStatus.partially_qualified


@pytest.mark.asyncio
async def test_early_goodbye(conv_manager):
    """Test early exit when caller says goodbye mid-qualification."""
    session = await conv_manager.create_session("sess_early_exit")
    await conv_manager.process_turn("sess_early_exit", TurnRequest(turn_id="t1", transcript="Yes sure"))
    await conv_manager.process_turn(
        "sess_early_exit",
        TurnRequest(turn_id="t2", transcript="We are Acme Digital, e-commerce"),
    )

    # Caller exits at size prompt
    t3 = await conv_manager.process_turn(
        "sess_early_exit",
        TurnRequest(turn_id="t3", transcript="Sorry, I have to go now, goodbye!"),
    )
    assert t3.conversation_state == ConversationState.ENDED
    assert t3.should_end_call is True
    assert t3.qualification_status == QualificationStatus.partially_qualified


@pytest.mark.asyncio
async def test_off_topic_preserves_state(conv_manager):
    """Test that off-topic inquiry does not erase current state."""
    session = await conv_manager.create_session("sess_offtopic")
    await conv_manager.process_turn("sess_offtopic", TurnRequest(turn_id="t1", transcript="Sure"))
    # Currently at ASK_COMPANY
    t2 = await conv_manager.process_turn(
        "sess_offtopic",
        TurnRequest(turn_id="t2", transcript="Can you tell me what the weather is today?"),
    )
    assert t2.intent == Intent.off_topic
    assert t2.conversation_state == ConversationState.ASK_COMPANY
    assert t2.should_end_call is False


@pytest.mark.asyncio
async def test_ambiguous_company_size_clarification(conv_manager):
    """Test ambiguous company size triggers CLARIFY_SIZE."""
    session = await conv_manager.create_session("sess_amb_size")
    await conv_manager.process_turn("sess_amb_size", TurnRequest(turn_id="t1", transcript="Sure"))
    await conv_manager.process_turn("sess_amb_size", TurnRequest(turn_id="t2", transcript="Acme Retail"))

    # Turn 3: Ambiguous answer
    t3 = await conv_manager.process_turn(
        "sess_amb_size",
        TurnRequest(turn_id="t3", transcript="We're a small company, just a few people."),
    )
    assert t3.conversation_state == ConversationState.CLARIFY_SIZE

    # Clarification answered
    t4 = await conv_manager.process_turn(
        "sess_amb_size",
        TurnRequest(turn_id="t4", transcript="Around 8 people."),
    )
    assert t4.conversation_state == ConversationState.ASK_BUDGET
    assert t4.lead.company_size == 8


@pytest.mark.asyncio
async def test_ambiguous_budget_clarification(conv_manager):
    """Test ambiguous budget without currency triggers CLARIFY_BUDGET."""
    session = await conv_manager.create_session("sess_amb_budget")
    await conv_manager.process_turn("sess_amb_budget", TurnRequest(turn_id="t1", transcript="Sure"))
    await conv_manager.process_turn("sess_amb_budget", TurnRequest(turn_id="t2", transcript="Acme Retail"))
    await conv_manager.process_turn("sess_amb_budget", TurnRequest(turn_id="t3", transcript="10 employees"))

    # Ambiguous budget without currency
    t4 = await conv_manager.process_turn(
        "sess_amb_budget",
        TurnRequest(turn_id="t4", transcript="We spend fifty thousand."),
    )
    assert t4.conversation_state == ConversationState.CLARIFY_BUDGET

    # Clarify currency and period
    t5 = await conv_manager.process_turn(
        "sess_amb_budget",
        TurnRequest(turn_id="t5", transcript="That is fifty thousand rupees a month."),
    )
    assert t5.conversation_state == ConversationState.ENDED
    assert t5.lead.budget_currency == "INR"
    assert t5.lead.budget_period == BudgetPeriod.monthly
    assert t5.qualification_status == QualificationStatus.qualified


@pytest.mark.asyncio
async def test_caller_correction(conv_manager):
    """Test caller correcting a previously stated employee count."""
    session = await conv_manager.create_session("sess_correction")
    await conv_manager.process_turn("sess_correction", TurnRequest(turn_id="t1", transcript="Yes"))
    await conv_manager.process_turn("sess_correction", TurnRequest(turn_id="t2", transcript="Acme Corp"))
    t3 = await conv_manager.process_turn(
        "sess_correction",
        TurnRequest(turn_id="t3", transcript="We have 25 employees."),
    )
    assert t3.lead.company_size == 25

    # Correction utterance
    t4 = await conv_manager.process_turn(
        "sess_correction",
        TurnRequest(turn_id="t4", transcript="Actually, make that 40 employees."),
    )
    assert t4.lead.company_size == 40


@pytest.mark.asyncio
async def test_session_already_ended_rejects_new_turns(conv_manager):
    """Test that submitting a turn to an ended session raises ValueError."""
    session = await conv_manager.create_session("sess_ended_reject")
    # End the session
    await conv_manager.process_turn("sess_ended_reject", TurnRequest(turn_id="t1", transcript="No, stop"))
    
    # Attempt next turn
    with pytest.raises(ValueError, match="Session has already ended"):
        await conv_manager.process_turn(
            "sess_ended_reject",
            TurnRequest(turn_id="t2", transcript="Can I continue?"),
        )


@pytest.mark.asyncio
async def test_max_clarification_attempts_proceeds(conv_manager):
    """Test that exceeding maximum clarification attempts accepts unknown and proceeds."""
    session = await conv_manager.create_session("sess_max_retry")
    await conv_manager.process_turn("sess_max_retry", TurnRequest(turn_id="t1", transcript="Yes"))
    await conv_manager.process_turn("sess_max_retry", TurnRequest(turn_id="t2", transcript="Acme"))

    # Attempt 1 ambiguous size -> CLARIFY_SIZE
    t3 = await conv_manager.process_turn(
        "sess_max_retry", TurnRequest(turn_id="t3", transcript="Not many people.")
    )
    assert t3.conversation_state == ConversationState.CLARIFY_SIZE

    # Attempt 2 ambiguous size -> CLARIFY_SIZE
    t4 = await conv_manager.process_turn(
        "sess_max_retry", TurnRequest(turn_id="t4", transcript="Still not sure.")
    )
    # Clarification limit reached -> proceeds to ASK_BUDGET
    assert t4.conversation_state == ConversationState.ASK_BUDGET
    assert t4.lead.company_size is None
