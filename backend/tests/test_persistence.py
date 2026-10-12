"""Tests for SQLite database persistence, uniqueness constraints, idempotency, and error handling."""

import pytest
from app.models.session import Session
from app.schemas.conversation import ConversationState, SessionStatus, Speaker
from app.schemas.lead import BudgetPeriod, QualificationStatus, ValidatedLead


@pytest.mark.asyncio
async def test_session_lifecycle_persistence(session_repo):
    """Test creating, saving, and retrieving a session from the repository."""
    session = Session(session_id="sess_db_001", current_state=ConversationState.GREETING)
    await session_repo.save_session(session)

    retrieved = await session_repo.get_session("sess_db_001")
    assert retrieved is not None
    assert retrieved.session_id == "sess_db_001"
    assert retrieved.current_state == ConversationState.GREETING
    assert retrieved.session_status == SessionStatus.active

    # Update session
    retrieved.current_state = ConversationState.ASK_SIZE
    retrieved.last_processed_turn_id = "turn_01"
    await session_repo.save_session(retrieved)

    updated = await session_repo.get_session("sess_db_001")
    assert updated.current_state == ConversationState.ASK_SIZE
    assert updated.last_processed_turn_id == "turn_01"


@pytest.mark.asyncio
async def test_lead_persistence_and_retrieval(session_repo, lead_repo):
    """Test saving a validated lead and retrieving it by session_id and lead_id."""
    await session_repo.save_session(Session(session_id="sess_lead_01"))
    lead = ValidatedLead(
        company_name="Test Enterprise",
        business_type="SaaS",
        company_size=50,
        marketing_budget=10000.0,
        budget_currency="USD",
        budget_period=BudgetPeriod.monthly,
    )
    saved = await lead_repo.save_lead(
        session_id="sess_lead_01",
        lead=lead,
        qualification_status=QualificationStatus.qualified,
    )

    assert saved.lead_id is not None
    assert saved.company_name == "Test Enterprise"
    assert saved.company_size == 50

    # Retrieve by session_id
    by_sess = await lead_repo.get_lead_by_session_id("sess_lead_01")
    assert by_sess is not None
    assert by_sess.lead_id == saved.lead_id

    # Retrieve by lead_id
    by_lead_id = await lead_repo.get_lead_by_id(saved.lead_id)
    assert by_lead_id is not None
    assert by_lead_id.session_id == "sess_lead_01"


@pytest.mark.asyncio
async def test_duplicate_lead_prevention(session_repo, lead_repo):
    """Test that saving a lead for the same session updates the record rather than duplicating."""
    await session_repo.save_session(Session(session_id="sess_unique_test"))
    lead_v1 = ValidatedLead(
        company_name="Acme V1",
        company_size=20,
        marketing_budget=5000.0,
        budget_currency="USD",
        budget_period=BudgetPeriod.monthly,
    )
    saved_v1 = await lead_repo.save_lead(
        session_id="sess_unique_test",
        lead=lead_v1,
        qualification_status=QualificationStatus.in_progress,
    )

    lead_v2 = ValidatedLead(
        company_name="Acme V2",
        company_size=25,
        marketing_budget=8000.0,
        budget_currency="USD",
        budget_period=BudgetPeriod.monthly,
    )
    saved_v2 = await lead_repo.save_lead(
        session_id="sess_unique_test",
        lead=lead_v2,
        qualification_status=QualificationStatus.qualified,
    )

    # Lead ID must remain identical and not duplicate in table
    assert saved_v1.lead_id == saved_v2.lead_id
    all_leads = await lead_repo.list_leads()
    matching = [l for l in all_leads if l.session_id == "sess_unique_test"]
    assert len(matching) == 1
    assert matching[0].company_name == "Acme V2"
    assert matching[0].company_size == 25


@pytest.mark.asyncio
async def test_duplicate_turn_handling(session_repo):
    """Test transcript turn insertion and idempotency detection."""
    session = Session(session_id="sess_turn_test")
    await session_repo.save_session(session)

    # First turn insert succeeds
    ins1 = await session_repo.add_transcript_turn(
        session_id="sess_turn_test",
        turn_id="turn_1",
        speaker=Speaker.caller,
        text="Hello there",
    )
    assert ins1 is True

    # Duplicate turn insert returns False
    ins2 = await session_repo.add_transcript_turn(
        session_id="sess_turn_test",
        turn_id="turn_1",
        speaker=Speaker.caller,
        text="Hello there again",
    )
    assert ins2 is False

    # Check has_turn
    assert await session_repo.has_turn("sess_turn_test", "turn_1") is True
    assert await session_repo.has_turn("sess_turn_test", "turn_nonexistent") is False


@pytest.mark.asyncio
async def test_session_finalization(conv_manager, session_repo, lead_repo):
    """Test explicit manual session finalization via end_session."""
    session = await conv_manager.create_session("sess_final")
    session, lead_saved, lead_id = await conv_manager.end_session("sess_final")

    assert session.current_state == ConversationState.ENDED
    assert session.session_status == SessionStatus.ended
    assert session.ended_at is not None
    assert lead_saved is True
    assert lead_id is not None
