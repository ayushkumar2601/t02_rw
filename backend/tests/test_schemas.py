"""Tests for Pydantic schemas validating canonical data models, strict constraints, and edge cases."""

import pytest
from pydantic import ValidationError

from app.schemas.conversation import (
    ConversationState,
    Intent,
    LLMExtractionResponse,
    SessionStatus,
    TurnRequest,
    TurnResponse,
)
from app.schemas.lead import (
    BudgetPeriod,
    CandidateLeadExtraction,
    PersistedLeadRecord,
    QualificationStatus,
    ValidatedLead,
)
from app.services.validation_service import validation_service


def test_valid_candidate_extraction():
    """Test valid candidate lead extraction parsing."""
    candidate = CandidateLeadExtraction(
        company_name="Acme Digital",
        business_type="E-commerce",
        company_size=25,
        marketing_budget=50000.0,
        budget_currency="INR",
        budget_period=BudgetPeriod.monthly,
        contact_name="Alice Smith",
        contact_email="alice@example.com",
    )
    assert candidate.company_name == "Acme Digital"
    assert candidate.company_size == 25
    assert candidate.marketing_budget == 50000.0
    assert candidate.budget_currency == "INR"
    assert candidate.budget_period == BudgetPeriod.monthly
    assert candidate.contact_email == "alice@example.com"


def test_candidate_rejects_negative_company_size():
    """Test that negative company size is rejected."""
    with pytest.raises(ValidationError):
        CandidateLeadExtraction(company_size=-5)


def test_candidate_rejects_negative_budget():
    """Test that negative budget is rejected."""
    with pytest.raises(ValidationError):
        CandidateLeadExtraction(marketing_budget=-100.0)


def test_candidate_rejects_unexpected_extra_fields():
    """Test that extra undocumented fields are forbidden."""
    with pytest.raises(ValidationError):
        CandidateLeadExtraction.model_validate(
            {"company_name": "Acme", "unauthorized_field": "hack"}
        )


def test_validated_lead_rejects_extra_fields():
    """Test that ValidatedLead forbids extra fields."""
    with pytest.raises(ValidationError):
        ValidatedLead.model_validate({"extra_key": "not_allowed"})


def test_invalid_budget_period_enum():
    """Test that invalid budget period enum raises ValidationError."""
    with pytest.raises(ValidationError):
        CandidateLeadExtraction.model_validate({"budget_period": "biweekly"})


def test_invalid_intent_enum():
    """Test that invalid intent raises ValidationError."""
    with pytest.raises(ValidationError):
        LLMExtractionResponse.model_validate(
            {
                "intent": "invalid_intent_value",
                "response": "Hello",
                "candidate_lead": {},
            }
        )


def test_invalid_conversation_state_enum():
    """Test that invalid conversation state raises ValidationError."""
    with pytest.raises(ValidationError):
        TurnResponse.model_validate(
            {
                "session_id": "sess_1",
                "turn_id": "t1",
                "intent": "lead_qualification",
                "conversation_state": "INVALID_STATE",
                "state": "INVALID_STATE",
                "response": "Hello",
                "lead": {},
                "missing_fields": [],
                "qualification_status": "in_progress",
                "should_end_call": False,
                "session_status": "active",
            }
        )


def test_invalid_email_format():
    """Test that malformed email is rejected by CandidateLeadExtraction."""
    with pytest.raises(ValidationError):
        CandidateLeadExtraction(contact_email="not-an-email")


def test_missing_fields_calculation():
    """Test backend computation of missing fields for qualification."""
    # Empty lead
    lead = ValidatedLead()
    missing = validation_service.compute_missing_fields(lead)
    assert "company_size" in missing
    assert "marketing_budget" in missing
    assert "budget_currency" in missing
    assert "budget_period" in missing

    # Partially filled lead
    lead.company_size = 10
    lead.marketing_budget = 5000.0
    missing = validation_service.compute_missing_fields(lead)
    assert "company_size" not in missing
    assert "marketing_budget" not in missing
    assert "budget_currency" in missing
    assert "budget_period" in missing

    # Fully filled lead
    lead.budget_currency = "USD"
    lead.budget_period = BudgetPeriod.monthly
    missing = validation_service.compute_missing_fields(lead)
    assert len(missing) == 0


def test_turn_request_validation():
    """Test TurnRequest validation rules."""
    # Valid turn
    req = TurnRequest(turn_id="turn_123", transcript="We have 10 people.")
    assert req.turn_id == "turn_123"

    # Empty turn_id should fail
    with pytest.raises(ValidationError):
        TurnRequest(turn_id="", transcript="Hello")

    # Extra fields should fail
    with pytest.raises(ValidationError):
        TurnRequest(turn_id="t1", transcript="Hello", extra="bad")


def test_llm_extraction_response_schema():
    """Test LLMExtractionResponse schema validation."""
    payload = {
        "intent": "lead_qualification",
        "suggested_state": "ASK_SIZE",
        "response": "Approximately how many people work at your company?",
        "candidate_lead": {
            "company_name": "Test Co",
            "business_type": "Marketing",
            "company_size": 15,
            "marketing_budget": 20000.0,
            "budget_currency": "USD",
            "budget_period": "monthly",
            "contact_name": None,
            "contact_email": None,
        },
        "clarification_needed": None,
        "should_end_call": False,
    }
    extracted = LLMExtractionResponse.model_validate(payload)
    assert extracted.intent == Intent.lead_qualification
    assert extracted.candidate_lead.company_size == 15
