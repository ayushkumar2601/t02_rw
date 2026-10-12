"""Tests for candidate extraction, natural language number & budget parsing, and fallback behaviors."""

import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.conversation import ConversationState, Intent, LLMExtractionResponse
from app.schemas.lead import BudgetPeriod, ValidatedLead
from app.services.extraction_service import ExtractionService
from app.services.llm_client import LLMRateLimitError, LLMTimeoutError
from app.services.validation_service import validation_service


def test_parse_spoken_number_phrases():
    """Test natural language parsing of employee counts."""
    assert validation_service.parse_spoken_number("it's just me") == 1
    assert validation_service.parse_spoken_number("its just me") == 1
    assert validation_service.parse_spoken_number("solo") == 1
    assert validation_service.parse_spoken_number("twenty-five") == 25
    assert validation_service.parse_spoken_number("twenty five") == 25
    assert validation_service.parse_spoken_number("we have 25 employees") == 25
    assert validation_service.parse_spoken_number("about fifty people") == 50
    assert validation_service.parse_spoken_number("around twelve team members") == 12
    assert validation_service.parse_spoken_number("one hundred") == 100
    assert validation_service.parse_spoken_number("we are a small company") is None


def test_parse_budget_utterance_scenarios():
    """Test budget extraction for amounts, currencies, and timeframes."""
    # Scenario A: Rupees per month
    amount, curr, period = validation_service.parse_budget_utterance("Around fifty thousand rupees a month")
    assert amount == 50000.0
    assert curr == "INR"
    assert period == BudgetPeriod.monthly

    # Scenario B: Indian notation - Five lakhs annually
    amount, curr, period = validation_service.parse_budget_utterance("Five lakhs annually")
    assert amount == 500000.0
    assert curr == "INR"
    assert period == BudgetPeriod.yearly

    # Scenario C: Dollars per month
    amount, curr, period = validation_service.parse_budget_utterance("About two thousand dollars a month")
    assert amount == 2000.0
    assert curr == "USD"
    assert period == BudgetPeriod.monthly

    # Scenario D: Ambiguous currency
    amount, curr, period = validation_service.parse_budget_utterance("We spend fifty thousand")
    assert amount == 50000.0
    assert curr is None
    assert period == BudgetPeriod.unknown

    # Scenario E: Symbol prefix
    amount, curr, period = validation_service.parse_budget_utterance("₹75,000 per month")
    assert amount == 75000.0
    assert curr == "INR"
    assert period == BudgetPeriod.monthly


@pytest.mark.asyncio
async def test_deterministic_fallback_intents():
    """Test deterministic fallback intent classification."""
    svc = ExtractionService()
    lead = ValidatedLead()
    missing = ["company_size", "marketing_budget", "budget_currency", "budget_period"]

    # Goodbye
    res = await svc.extract_candidate("I have to go now, goodbye", ConversationState.ASK_SIZE, lead, missing)
    assert res.intent == Intent.goodbye
    assert res.should_end_call is True

    # Human request
    res = await svc.extract_candidate("Can I speak to a real human person?", ConversationState.ASK_COMPANY, lead, missing)
    assert res.intent == Intent.human_request
    assert "AI assistant" in res.response

    # Off-topic
    res = await svc.extract_candidate("Tell me a funny joke", ConversationState.ASK_SIZE, lead, missing)
    assert res.intent == Intent.off_topic

    # Unclear
    res = await svc.extract_candidate("uhhh what", ConversationState.ASK_BUDGET, lead, missing)
    assert res.intent == Intent.unclear


@pytest.mark.asyncio
async def test_extraction_with_mocked_llm_success():
    """Test extraction service when LLM client returns valid JSON."""
    mock_client = AsyncMock()
    mock_client.is_configured = True
    mock_client.generate_chat_completion.return_value = """
    {
      "intent": "lead_qualification",
      "suggested_state": "ASK_SIZE",
      "response": "Got it! Approximately how many employees work at Acme?",
      "candidate_lead": {
        "company_name": "Acme Digital",
        "business_type": "E-commerce",
        "company_size": null,
        "marketing_budget": null,
        "budget_currency": null,
        "budget_period": "unknown",
        "contact_name": null,
        "contact_email": null
      },
      "clarification_needed": null,
      "should_end_call": false
    }
    """

    svc = ExtractionService(client=mock_client)
    res = await svc.extract_candidate("We are Acme Digital, an e-commerce shop", ConversationState.ASK_COMPANY, ValidatedLead(), [])
    assert res.intent == Intent.lead_qualification
    assert res.candidate_lead.company_name == "Acme Digital"
    assert res.candidate_lead.business_type == "E-commerce"


@pytest.mark.asyncio
async def test_extraction_bounded_repair_on_markdown_wrapped_json():
    """Test that extraction repairs JSON wrapped in markdown or whitespace."""
    mock_client = AsyncMock()
    mock_client.is_configured = True
    # Simulated markdown wrapped text
    mock_client.generate_chat_completion.return_value = """
    Here is the response:
    {
      "intent": "lead_qualification",
      "suggested_state": "ASK_BUDGET",
      "response": "Thanks. Approximately how much do you spend on marketing each month?",
      "candidate_lead": {
        "company_name": null,
        "business_type": null,
        "company_size": 25,
        "marketing_budget": null,
        "budget_currency": null,
        "budget_period": "unknown",
        "contact_name": null,
        "contact_email": null
      },
      "clarification_needed": null,
      "should_end_call": false
    }
    """

    svc = ExtractionService(client=mock_client)
    res = await svc.extract_candidate("We have 25 employees", ConversationState.ASK_SIZE, ValidatedLead(), [])
    assert res.candidate_lead.company_size == 25


@pytest.mark.asyncio
async def test_extraction_fallback_on_llm_rate_limit():
    """Test that rate limit exception safely triggers deterministic fallback without crashing."""
    mock_client = AsyncMock()
    mock_client.is_configured = True
    mock_client.generate_chat_completion.side_effect = LLMRateLimitError("HTTP 429")

    svc = ExtractionService(client=mock_client)
    res = await svc.extract_candidate("We have 25 employees", ConversationState.ASK_SIZE, ValidatedLead(), ["company_size"])
    # Fallback extracts the number 25
    assert res.candidate_lead.company_size == 25


def test_parse_company_and_business_type():
    """Test company name and business type extraction from varied natural language phrasing."""
    # User's exact case:
    c_name, b_type = validation_service.parse_company_info(
        "companies name is tectrongo and the business is digital marketing"
    )
    assert c_name == "Tectrongo"
    assert b_type == "Digital Marketing"

    # Variant: "company's name is..."
    c_name, b_type = validation_service.parse_company_info(
        "company's name is tectrongo and the business is digital marketing"
    )
    assert c_name == "Tectrongo"
    assert b_type == "Digital Marketing"

    # Variant: "company name is..."
    c_name, b_type = validation_service.parse_company_info(
        "company name is tectrongo and the business is digital marketing"
    )
    assert c_name == "Tectrongo"
    assert b_type == "Digital Marketing"

    # Variant: "we are an e-commerce company called Acme Digital"
    c_name, b_type = validation_service.parse_company_info(
        "we are an e-commerce company called Acme Digital"
    )
    assert c_name == "Acme Digital"
    assert b_type == "E-commerce"

    # Variant: Comma separated
    c_name, b_type = validation_service.parse_company_info("Acme Digital, e-commerce")
    assert c_name == "Acme Digital"
    assert b_type == "E-commerce"

    # Variant: Comma separated with digital marketing
    c_name, b_type = validation_service.parse_company_info("Tectrongo, digital marketing")
    assert c_name == "Tectrongo"
    assert b_type == "Digital Marketing"

    # Variant: Direct company name in ASK_COMPANY state
    c_name, b_type = validation_service.parse_company_info("Tectrongo", is_ask_company_state=True)
    assert c_name == "Tectrongo"

