"""Integration tests for all FastAPI REST endpoints using httpx AsyncClient."""

import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.conversation import ConversationState, SessionStatus
from app.services.llm_client import LLMRateLimitError, LLMTimeoutError


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client):
    """Test GET /health returns 200 with service information and masks secrets."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "llm_mode" in data
    # Ensure no secrets leaked
    assert "api_key" not in data
    assert "key" not in data


@pytest.mark.asyncio
async def test_session_creation(async_client):
    """Test POST /api/sessions creates a session and returns initial greeting."""
    resp = await async_client.post("/api/sessions")
    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data
    assert data["state"] == "GREETING"
    assert data["status"] == "active"
    assert "Ava" in data["greeting"]


@pytest.mark.asyncio
async def test_process_turn_happy_path(async_client):
    """Test POST /api/sessions/{session_id}/turns advances conversation."""
    create_resp = await async_client.post("/api/sessions")
    session_id = create_resp.json()["session_id"]

    # Turn 1: Agree to talk
    turn_resp = await async_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"turn_id": "turn_1", "transcript": "Yes, sounds good."},
    )
    assert turn_resp.status_code == 200
    t1_data = turn_resp.json()
    assert t1_data["session_id"] == session_id
    assert t1_data["turn_id"] == "turn_1"
    assert t1_data["conversation_state"] == "ASK_COMPANY"
    assert t1_data["should_end_call"] is False


@pytest.mark.asyncio
async def test_process_turn_invalid_payload(async_client):
    """Test that invalid payload returns 422."""
    create_resp = await async_client.post("/api/sessions")
    session_id = create_resp.json()["session_id"]

    # Missing turn_id
    resp = await async_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"transcript": "Hello"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_process_turn_unknown_session(async_client):
    """Test that submitting turn to unknown session returns 404."""
    resp = await async_client.post(
        "/api/sessions/sess_nonexistent/turns",
        json={"turn_id": "t1", "transcript": "Hello"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_process_turn_idempotency(async_client):
    """Test duplicate turn submission returns idempotent response."""
    create_resp = await async_client.post("/api/sessions")
    session_id = create_resp.json()["session_id"]

    # First submission
    resp1 = await async_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"turn_id": "duplicate_turn_1", "transcript": "Yes, please."},
    )
    assert resp1.status_code == 200

    # Second submission with exact same turn_id
    resp2 = await async_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"turn_id": "duplicate_turn_1", "transcript": "Yes, please."},
    )
    assert resp2.status_code == 200
    assert resp2.json()["turn_id"] == "duplicate_turn_1"
    assert resp2.json()["conversation_state"] == resp1.json()["conversation_state"]


@pytest.mark.asyncio
async def test_get_session_details(async_client):
    """Test GET /api/sessions/{session_id} returns state and transcript."""
    create_resp = await async_client.post("/api/sessions")
    session_id = create_resp.json()["session_id"]

    await async_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"turn_id": "t1", "transcript": "Yes"},
    )

    get_resp = await async_client.get(f"/api/sessions/{session_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["session_id"] == session_id
    assert len(data["transcript"]) >= 2  # greeting + caller utterance + agent response


@pytest.mark.asyncio
async def test_end_session_endpoint(async_client):
    """Test POST /api/sessions/{session_id}/end finalizes session."""
    create_resp = await async_client.post("/api/sessions")
    session_id = create_resp.json()["session_id"]

    end_resp = await async_client.post(f"/api/sessions/{session_id}/end")
    assert end_resp.status_code == 200
    data = end_resp.json()
    assert data["session_id"] == session_id
    assert data["status"] == "ended"
    assert data["lead_saved"] is True


@pytest.mark.asyncio
async def test_leads_endpoints(async_client):
    """Test GET /api/leads and GET /api/leads/{lead_id}."""
    # Complete a session to create a lead
    create_resp = await async_client.post("/api/sessions")
    session_id = create_resp.json()["session_id"]

    await async_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"turn_id": "t1", "transcript": "Yes, we run Acme Digital, e-commerce."},
    )
    await async_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"turn_id": "t2", "transcript": "We have 15 employees."},
    )
    await async_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"turn_id": "t3", "transcript": "We spend $5000 a month on marketing."},
    )

    # List leads
    leads_resp = await async_client.get("/api/leads")
    assert leads_resp.status_code == 200
    leads_data = leads_resp.json()
    assert len(leads_data) >= 1
    target_lead = leads_data[0]
    lead_id = target_lead["lead_id"]

    # Get single lead
    single_resp = await async_client.get(f"/api/leads/{lead_id}")
    assert single_resp.status_code == 200
    assert single_resp.json()["lead_id"] == lead_id


@pytest.mark.asyncio
async def test_provider_failure_and_timeout_resilience(async_client, monkeypatch):
    """Test that LLM provider timeout gracefully falls back to deterministic extraction."""
    create_resp = await async_client.post("/api/sessions")
    session_id = create_resp.json()["session_id"]

    import app.services.llm_client
    mock_generate = AsyncMock(side_effect=LLMTimeoutError("Request timed out"))
    monkeypatch.setattr(app.services.llm_client.llm_client, "api_key", "mock_api_key")
    monkeypatch.setattr(
        app.services.llm_client.llm_client, "generate_chat_completion", mock_generate
    )

    # Submitting turn under simulated LLM timeout
    turn_resp = await async_client.post(
        f"/api/sessions/{session_id}/turns",
        json={"turn_id": "t_timeout", "transcript": "Yes, we have 25 employees."},
    )
    assert turn_resp.status_code == 200
    data = turn_resp.json()
    # Still succeeds through deterministic fallback!
    assert data["session_id"] == session_id
