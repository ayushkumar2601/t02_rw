# Automated Test Execution Report: Ava Inbound Voice Agent

**Date of Execution:** 2026-10-13  
**Python Environment:** Python 3.11.16  
**Test Framework:** Pytest 8.4.2 with `pytest-asyncio` 0.26.0  
**Overall Status:** PASSED (43 / 43 tests passing, 0 failures, 0 errors)  
**Execution Time:** 0.36 seconds  

---

## 1. Test Execution Command and Raw Output

### Command
```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/ -v
```

### Pytest Console Summary
```text
============================= test session starts ==============================
platform darwin -- Python 3.11.16, pytest-8.4.2, pluggy-1.6.0 -- backend/.venv/bin/python3.11
cachedir: .pytest_cache
rootdir: /Users/ayush/Desktop/task02_reno
plugins: asyncio-0.26.0, anyio-4.15.1
asyncio: mode=Mode.STRICT, asyncio_default_test_loop_scope=function
collected 43 items

backend/tests/test_api.py::test_health_check_endpoint PASSED             [  2%]
backend/tests/test_api.py::test_session_creation PASSED                  [  4%]
backend/tests/test_api.py::test_process_turn_happy_path PASSED           [  7%]
backend/tests/test_api.py::test_process_turn_invalid_payload PASSED      [  9%]
backend/tests/test_api.py::test_process_turn_unknown_session PASSED      [ 11%]
backend/tests/test_api.py::test_process_turn_idempotency PASSED          [ 14%]
backend/tests/test_api.py::test_get_session_details PASSED               [ 16%]
backend/tests/test_api.py::test_end_session_endpoint PASSED              [ 19%]
backend/tests/test_api.py::test_leads_endpoints PASSED                   [ 21%]
backend/tests/test_api.py::test_provider_failure_and_timeout_resilience PASSED [ 23%]
backend/tests/test_extraction.py::test_parse_spoken_number_phrases PASSED [ 26%]
backend/tests/test_extraction.py::test_parse_budget_utterance_scenarios PASSED [ 28%]
backend/tests/test_extraction.py::test_deterministic_fallback_intents PASSED [ 30%]
backend/tests/test_extraction.py::test_extraction_with_mocked_llm_success PASSED [ 32%]
backend/tests/test_extraction.py::test_extraction_bounded_repair_on_markdown_wrapped_json PASSED [ 34%]
backend/tests/test_extraction.py::test_extraction_fallback_on_llm_rate_limit PASSED [ 37%]
backend/tests/test_extraction.py::test_parse_company_and_business_type PASSED [ 39%]
backend/tests/test_persistence.py::test_session_lifecycle_persistence PASSED [ 41%]
backend/tests/test_persistence.py::test_lead_persistence_and_retrieval PASSED [ 44%]
backend/tests/test_duplicate_lead_prevention PASSED [ 46%]
backend/tests/test_duplicate_turn_handling PASSED   [ 48%]
backend/tests/test_session_finalization PASSED      [ 51%]
backend/tests/test_schemas.py::test_valid_candidate_extraction PASSED    [ 53%]
backend/tests/test_schemas.py::test_candidate_rejects_negative_company_size PASSED [ 55%]
backend/tests/test_candidate_rejects_negative_budget PASSED [ 58%]
backend/tests/test_schemas.py::test_candidate_rejects_unexpected_extra_fields PASSED [ 60%]
backend/tests/test_schemas.py::test_validated_lead_rejects_extra_fields PASSED [ 62%]
backend/tests/test_schemas.py::test_invalid_budget_period_enum PASSED    [ 65%]
backend/tests/test_schemas.py::test_invalid_intent_enum PASSED           [ 67%]
backend/tests/test_schemas.py::test_invalid_conversation_state_enum PASSED [ 69%]
backend/tests/test_schemas.py::test_invalid_email_format PASSED          [ 72%]
backend/tests/test_schemas.py::test_missing_fields_calculation PASSED    [ 74%]
backend/tests/test_schemas.py::test_turn_request_validation PASSED       [ 76%]
backend/tests/test_schemas.py::test_llm_extraction_response_schema PASSED [ 79%]
backend/tests/test_state_machine.py::test_normal_qualification_workflow PASSED [ 81%]
backend/tests/test_state_machine.py::test_caller_declines_at_greeting PASSED [ 83%]
backend/tests/test_state_machine.py::test_early_goodbye PASSED           [ 86%]
backend/tests/test_state_machine.py::test_off_topic_preserves_state PASSED [ 88%]
backend/tests/test_state_machine.py::test_ambiguous_company_size_clarification PASSED [ 90%]
backend/tests/test_state_machine.py::test_ambiguous_budget_clarification PASSED [ 93%]
backend/tests/test_state_machine.py::test_caller_correction PASSED       [ 95%]
backend/tests/test_state_machine.py::test_session_already_ended_rejects_new_turns PASSED [ 97%]
backend/tests/test_state_machine.py::test_max_clarification_attempts_proceeds PASSED [100%]

============================== 43 passed in 0.36s ==============================
```

---

## 2. Test Suite Breakdown by Module

### A. Schema & Data Model Tests (`tests/test_schemas.py` - 12 Tests)
- `test_valid_candidate_extraction`: Validates parsing of standard candidate attributes.
- `test_candidate_rejects_negative_company_size`: Enforces `ge=0` validation.
- `test_candidate_rejects_negative_budget`: Enforces non-negative marketing budgets.
- `test_candidate_rejects_unexpected_extra_fields`: Strict Pydantic `extra="forbid"` enforcement.
- `test_validated_lead_rejects_extra_fields`: Verifies server model rejects injected attributes.
- `test_invalid_budget_period_enum`: Rejects non-canonical periods.
- `test_invalid_intent_enum`: Rejects invalid intents.
- `test_invalid_conversation_state_enum`: Rejects unknown workflow states.
- `test_invalid_email_format`: Validates regex format for optional contact email.
- `test_missing_fields_calculation`: Tests backend missing qualification field list logic.
- `test_turn_request_validation`: Tests bounds on turn identifiers and payloads.
- `test_llm_extraction_response_schema`: Tests LLM candidate response model.

### B. Extraction & NLP Tests (`tests/test_extraction.py` - 6 Tests)
- `test_parse_spoken_number_phrases`: Tests natural spoken number parsing ("twenty-five" -> 25, "it's just me" -> 1, "about fifty people" -> 50).
- `test_parse_budget_utterance_scenarios`: Tests budget extraction ("₹50,000 per month", "five lakhs annually", "$2000 a month", ambiguous budgets).
- `test_deterministic_fallback_intents`: Tests intent classification under offline fallback mode (goodbye, human request, off-topic, unclear).
- `test_extraction_with_mocked_llm_success`: Tests parsing when mock LLM outputs valid JSON.
- `test_extraction_bounded_repair_on_markdown_wrapped_json`: Tests JSON repair when model wraps JSON with markdown fences.
- `test_extraction_fallback_on_llm_rate_limit`: Tests graceful fallback when provider returns HTTP 429.

### C. State Machine Tests (`tests/test_state_machine.py` - 9 Tests)
- `test_normal_qualification_workflow`: End-to-end multi-turn happy path leading to qualified lead.
- `test_caller_declines_at_greeting`: Graceful exit when caller declines initial greeting.
- `test_early_goodbye`: Early exit mid-qualification preserving collected data as `partially_qualified`.
- `test_off_topic_preserves_state`: Off-topic question acknowledged while preserving pending qualification state.
- `test_ambiguous_company_size_clarification`: Ambiguous size triggers `CLARIFY_SIZE`.
- `test_ambiguous_budget_clarification`: Ambiguous budget without currency triggers `CLARIFY_BUDGET`.
- `test_caller_correction`: Caller correction ("Actually, make that 40") updates existing field without duplication.
- `test_session_already_ended_rejects_new_turns`: Rejects turns to completed sessions with `ValueError`.
- `test_max_clarification_attempts_proceeds`: Exceeding clarification attempts accepts `null` and continues workflow.

### D. Persistence Tests (`tests/test_persistence.py` - 5 Tests)
- `test_session_lifecycle_persistence`: Tests session creation, state update, and retrieval in SQLite.
- `test_lead_persistence_and_retrieval`: Tests saving validated lead and retrieval by `lead_id` and `session_id`.
- `test_duplicate_lead_prevention`: Enforces UNIQUE constraint on `session_id` to prevent duplicate lead rows on retries.
- `test_duplicate_turn_handling`: Tests turn insertion idempotency detection in `transcript_turns`.
- `test_session_finalization`: Tests manual session finalization and lead creation.

### E. API Integration Tests (`tests/test_api.py` - 10 Tests)
- `test_health_check_endpoint`: Verifies `GET /health` returns 200 without exposing secrets.
- `test_session_creation`: Tests `POST /api/sessions` initializes `GREETING` state and session ID.
- `test_process_turn_happy_path`: Tests `POST /api/sessions/{id}/turns` advances conversation.
- `test_process_turn_invalid_payload`: Verifies HTTP 422 on invalid turn request.
- `test_process_turn_unknown_session`: Verifies HTTP 404 when session ID is not found.
- `test_process_turn_idempotency`: Verifies repeated turn ID returns idempotent response.
- `test_get_session_details`: Verifies `GET /api/sessions/{id}` returns complete transcript and lead data.
- `test_end_session_endpoint`: Verifies `POST /api/sessions/{id}/end` finalizes session.
- `test_leads_endpoints`: Verifies `GET /api/leads` and `GET /api/leads/{id}`.
- `test_provider_failure_and_timeout_resilience`: Verifies API handles LLM timeout via deterministic fallback.
