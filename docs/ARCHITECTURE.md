# Architecture Specification: Autonomous Inbound Voice Agent (Ava SDR)

## 1. Executive Summary and Problem Statement

Digital marketing agencies receive substantial volumes of inbound prospect enquiries across web forms, chat, and phone calls. Many prospects drop off when faced with static multi-page forms, while sales teams spend significant time qualifying leads manually.

**Ava** is an autonomous AI-powered Sales Development Representative (SDR) designed to conduct natural, structured inbound qualification conversations. Ava introduces itself as an AI assistant, gathers company information, team size, and approximate marketing budget, validates caller inputs, preserves determinism, handles interruptions, and produces strictly valid structured lead records.

### Phase 1 Scope & Boundary
Phase 1 implements the complete core backend, state machine intelligence, natural language extraction service, canonical Pydantic v2 schemas, and SQLite persistence. It provides full functionality via text-based REST APIs before the browser-based Web Speech interface is added in Phase 2.

---

## 2. Component Architecture and Trust Boundaries

The system is structured into modular layers with strict trust boundaries:

```
+-------------------------------------------------------------+
|                Phase 2: Browser Voice Client                |
|  (Web Speech API Recognition & SpeechSynthesis Playback)   |
+------------------------------+------------------------------+
                               | Untrusted HTTP Requests
                               v
+-------------------------------------------------------------+
|                     FastAPI REST Layer                      |
|           /api/sessions, /turns, /end, /leads, /health      |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|              Deterministic Conversation Manager             |
|   (Owns state transitions, retry budgets, global policies)  |
+---------------+------------------------------+--------------+
                |                              |
                v                              v
+-------------------------------+  +--------------------------+
|     LLM Extraction Service    |  | Validation & Policy      |
|  (Groq API / Deterministic    |  | (Canonical schemas,      |
|   NLP Extraction Fallback)    |  |  missing_fields, bounds) |
+---------------+---------------+  +------------+-------------+
                |                               |
                +---------------+---------------+
                                | Validated State
                                v
+-------------------------------------------------------------+
|                 Repository & Persistence Layer              |
|        aiosqlite (Sessions, Turns, Leads - SQLite DB)       |
+-------------------------------------------------------------+
```

### Component Breakdown

1. **API Router Layer (`backend/app/api/`)**:
   - `sessions.py`: Manages session creation (`POST /api/sessions`), turn processing (`POST /api/sessions/{id}/turns`), session detail (`GET /api/sessions/{id}`), and session closing (`POST /api/sessions/{id}/end`).
   - `leads.py`: Manages lead record querying in reverse chronological order (`GET /api/leads`) and single lead retrieval (`GET /api/leads/{id}`).
   - Health check (`GET /health`): Exposes operational status without exposing environment keys.

2. **Conversation Manager (`backend/app/services/conversation_manager.py`)**:
   - The authoritative owner of workflow progression.
   - Enforces the deterministic state machine (`GREETING -> ASK_COMPANY -> ASK_SIZE -> ASK_BUDGET -> SAVE_LEAD -> CLOSING -> ENDED`).
   - Manages clarification limits (maximum 1 clarification retry for ambiguous answers).
   - Enforces global transitions: Goodbye, Human representative request, Off-topic questions, Unclear utterances, and Caller corrections.
   - Never allows the LLM to skip states or fabricate state transitions.

3. **LLM Extraction Service (`backend/app/services/extraction_service.py` & `llm_client.py`)**:
   - Assembles structured context (current state, validated lead data collected so far, missing fields, caller utterance).
   - Injects the system prompt (`backend/app/prompts/sdr_system_prompt.txt`).
   - Invokes Groq API using JSON mode (`llama-3.3-70b-versatile`) with bounded retries and exponential backoff on HTTP 429 and timeouts.
   - Implements bounded JSON repair for wrapped or malformed responses.
   - Provides a comprehensive deterministic NLP fallback engine when `GROQ_API_KEY` is not provided or quota is exhausted, ensuring 100% operation at ₹0 cost.

4. **Validation and Policy Layer (`backend/app/services/validation_service.py`)**:
   - Computes `missing_fields` deterministically: `company_size`, `marketing_budget`, `budget_currency`, and `budget_period`.
   - Computes `qualification_status`: `in_progress`, `qualified`, `partially_qualified`, or `disqualified`.
   - Merges candidate extractions into validated leads without overwriting established valid data.
   - Normalizes spoken numbers ("twenty-five" -> 25, "it's just me" -> 1) and budgets ("fifty thousand rupees a month" -> 50000, INR, monthly).

5. **Repository & Persistence Layer (`backend/app/repositories/`)**:
   - `database.py`: Manages SQLite schema creation with foreign keys (`PRAGMA foreign_keys = ON;`), indexing, and async connections.
   - `session_repository.py`: Persists session records, serialized in-progress lead JSON, and transcript turns. Enforces turn idempotency via unique constraints.
   - `lead_repository.py`: Persists validated lead records with a unique constraint on `session_id`, ensuring one session never creates duplicate leads.

---

## 3. Request Lifecycle and Turn Execution

For each inbound utterance:
1. **Client Submission**: Client sends `turn_id` and `transcript` to `POST /api/sessions/{session_id}/turns`.
2. **Session & Idempotency Check**: Server checks if session is active. If `turn_id` was already processed, returns the previous response idempotently.
3. **Caller Transcript Log**: Turn is inserted into `transcript_turns` table with `speaker="caller"`.
4. **Natural Language Extraction**: Extraction service queries Groq LLM (or deterministic fallback) with strict JSON output contract.
5. **Candidate Validation & Merge**: Candidate fields are validated with Pydantic v2 and merged into `session.validated_lead`.
6. **State Transition**: State machine evaluates utterance and intent against current state rules and global policies.
7. **Persistence Trigger**: If transitioning to terminal state (`SAVE_LEAD`, `CLOSING`, `ENDED`), lead record is saved to SQLite.
8. **Agent Response Log**: Agent response is inserted into `transcript_turns` with `speaker="agent"`.
9. **Client Contract Delivery**: Server returns `TurnResponse` containing session ID, response text, current state, validated lead data, missing fields, qualification status, and call termination flags.

---

---

## 4. Zero-Cost Policy and Free-Tier Assumptions

- **Total External Spend**: Exactly ₹0.
- **Dependencies**: 100% open-source (Python 3.11, FastAPI, Pydantic v2, aiosqlite, HTTPX, Pytest, Next.js, Tailwind CSS, Lucide React).
- **Voice Tier**: Native browser Web Speech API (`webkitSpeechRecognition` & `SpeechSynthesisUtterance`) requiring ₹0 external telephony or paid voice services.
- **LLM Provider**: Optional Groq API free developer tier (`llama-3.3-70b-versatile` / `llama-3.1-8b-instant`).
- **Offline / Zero-Quota Resilience**: If no Groq API key is configured or quota is exhausted, the backend automatically activates the internal deterministic NLP engine. All tests run offline with zero API calls.
- **Database**: Local zero-cost SQLite database (`leads.db`) with zero external service requirements.

---

## 5. Phase 2: Voice Interface and Acoustic Echo Mitigation Architecture

### Browser Voice Pipeline
The Phase 2 frontend is built as a reactive Next.js 16 dashboard connected to the FastAPI backend via type-safe REST calls:
- **Speech Recognition**: Uses browser-native `SpeechRecognition` / `webkitSpeechRecognition` with continuous listening and interim feedback.
- **Speech Synthesis**: Uses browser-native `window.speechSynthesis` with natural English voice selection.
- **Real-Time Synchronized State**: Exposes live conversation transcript, structured lead inspection cards, missing field badges, and a live SQLite persisted leads table.
- **Text Fallback Mode**: Provides an inline text input allowing callers to type responses or corrections even if the microphone is muted or unavailable.

### Acoustic Self-Capture / Echo Elimination Architecture
When running in a laptop speaker and microphone environment without physical headphones, the laptop microphone picks up audio output from the laptop speaker (acoustic feedback loop). Ava implements a multi-layer acoustic echo defense system:

1. **Strict Sequential Half-Duplex Turn Taking**:
   - Before Ava speaks, `recognition.abort()` is immediately invoked and `isSpeakingRef.current = true`. The microphone is paused while speech synthesis is active.
   - While Ava is speaking, `recognition.onend` is barred from restarting speech recognition.
   - When Ava finishes speaking (`utterance.onend`), an acoustic dissipation cooldown timer (600ms) pauses re-activation until speaker reverberation in the room and laptop mic audio buffers completely dissipate.
   - Recognition is only re-enabled once the cooldown expires, transitioning the UI state badge to `Listening to you (Speak now)`.

2. **Multi-Layer Transcript Echo Suppression**:
   - The hook records Ava's spoken utterance in `lastSpokenAgentTextRef.current`.
   - Any recognition transcript captured during speech or cooldown is discarded immediately.
   - The `isAcousticEcho` filter compares transcript tokens against Ava's last spoken statement. If speaker bleed matches Ava's own words (e.g. "Could you clarify"), the transcript is discarded and prevented from creating a caller turn.

3. **Manual Interrupt Button ("Interrupt Ava")**:
   - Because acoustic mic barge-in creates speaker feedback loops on laptop speakers, a dedicated UI "Interrupt Ava" button appears whenever Ava is speaking.
   - Clicking "Interrupt Ava" immediately executes `window.speechSynthesis.cancel()`, clears speech buffers, flushes audio hardware, and re-activates the microphone so the user can speak immediately.

---

## 6. Natural Language Fact Extraction Engine

The extraction engine (`ValidationService` and `ExtractionService`) extracts caller facts from varied conversational phrasing:
- **Company Name**: Recognizes patterns including `companies name is <NAME>`, `company is <NAME>`, `called <NAME>`, `named <NAME>`, comma-delimited pairs (`Acme, marketing`), and direct answers in `ASK_COMPANY` state. Automatically title-cases cleaned company names.
- **Business Type / Industry**: Matches a comprehensive catalog of 30+ business domains (e.g., Digital Marketing, SEO, SaaS, E-commerce, Real Estate, Healthcare, Finance) as well as dynamic syntactic phrases (`business is <X>`, `we do <X>`).
- **Team Size**: Converts spoken numerals ("twenty-five", "solo", "it's just me", "tour/two member company") to integer employee counts.
- **Budget**: Extracts numeric values, denominations (k, thousand, lakh, crore), currencies (INR, USD, EUR, GBP), and billing periods (monthly, yearly, one-time).

