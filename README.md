# Autonomous Inbound Voice Agent — Ava (Phase 1)

Autonomous AI Sales Development Representative (SDR) backend for a digital marketing agency, built with FastAPI, Pydantic v2, Groq LLM integration (with deterministic offline fallback), and SQLite.

Ava qualifies inbound prospective client enquiries by introducing itself, capturing company details, team size, and marketing budget, validating answers, handling edge cases, and storing structured lead records.

Phase 1 delivers the complete backend agent intelligence and REST API foundation. Phase 2 introduces the browser-based Web Speech interface.

---

## Key Features

- **Polite AI Identity:** Introduces itself transparently as Ava, an AI SDR for the digital marketing agency.
- **Deterministic State Machine:** Backend owns all workflow transitions (`GREETING -> ASK_COMPANY -> ASK_SIZE -> ASK_BUDGET -> SAVE_LEAD -> CLOSING -> ENDED`).
- **Canonical Pydantic v2 Validation:** Strict JSON contracts with `extra="forbid"`, non-negative constraints, and server-side calculation of `missing_fields` and `qualification_status`.
- **Zero-Cost ($0) Architecture:** Fully functional with free and open-source tools. Works out-of-the-box using the deterministic NLP fallback engine without requiring a paid LLM key.
- **Natural Language Parsing:** Normalizes natural language numbers ("twenty-five" -> 25, "it's just me" -> 1) and budgets ("fifty thousand rupees a month" -> 50000, INR, monthly; "five lakhs annually" -> 500000, INR, yearly).
- **Comprehensive Edge-Case Handling:**
  - Ambiguous answers (clarify once, then proceed).
  - Off-topic questions (brief answer + redirect to pending question).
  - Human representative requests (truthful disclosure of AI status).
  - Early exit / caller declines (clean closing, partial lead saved).
  - Caller corrections (updates existing record without duplication).
  - Idempotent turn processing (duplicate `turn_id` submissions return safely).
- **SQLite Persistence:** Atomic storage of sessions, transcript turns, and validated leads with foreign keys and uniqueness constraints.

---

## Repository Structure

```text
task02_reno/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application entrypoint & lifespan
│   │   ├── config.py                   # Pydantic BaseSettings & environment configs
│   │   ├── api/
│   │   │   ├── sessions.py             # Session lifecycle & turn endpoints
│   │   │   └── leads.py                # Lead listing & retrieval endpoints
│   │   ├── schemas/
│   │   │   ├── conversation.py         # State machine, intents, and turn contracts
│   │   │   └── lead.py                 # ValidatedLead, candidate, and persisted models
│   │   ├── models/
│   │   │   └── session.py              # In-memory domain session model
│   │   ├── services/
│   │   │   ├── conversation_manager.py # Authoritative state machine engine
│   │   │   ├── extraction_service.py   # Context assembly & NLP fallback
│   │   │   ├── validation_service.py   # Deterministic validation & number parser
│   │   │   └── llm_client.py           # Groq API client with bounded retries
│   │   ├── repositories/
│   │   │   ├── database.py             # SQLite connection manager & schema init
│   │   │   ├── session_repository.py   # Session & transcript persistence
│   │   │   └── lead_repository.py      # Validated lead persistence & deduplication
│   │   └── prompts/
│   │       └── sdr_system_prompt.txt   # System prompt for Ava SDR
│   ├── tests/
│   │   ├── conftest.py                 # Pytest fixtures & test database isolation
│   │   ├── test_schemas.py             # Schema & validation constraint tests (12 tests)
│   │   ├── test_extraction.py          # NLP parsing & fallback tests (6 tests)
│   │   ├── test_state_machine.py       # State machine & edge case tests (9 tests)
│   │   ├── test_persistence.py         # SQLite persistence & idempotency tests (5 tests)
│   │   └── test_api.py                 # FastAPI integration tests (10 tests)
│   ├── requirements.txt                # Python dependencies
│   └── .env.example                    # Environment variable template
├── docs/
│   ├── ARCHITECTURE.md                 # Component architecture & trust boundaries
│   ├── FLOWCHART.md                    # State machine flowchart & transition rules
│   └── TEST_RESULTS.md                 # Test suite execution report (42 passing tests)
├── .gitignore
├── PRD.md
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python 3.11** or compatible Python version.
- **Git**

### 1. Installation

Clone the repository and set up a Python virtual environment:

```bash
cd task02_reno

# Create virtual environment with Python 3.11
python3.11 -m venv backend/.venv

# Activate virtual environment
source backend/.venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 2. Environment Configuration

Copy the example environment configuration:

```bash
cp backend/.env.example backend/.env
```

The system is configured to run in **offline deterministic mode** by default ($0 cost). If you have an accessible free developer API key from [Groq](https://console.groq.com), you may optionally set it in `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

*Note: Tests and local execution run 100% offline without requiring an API key.*

### 3. Running Automated Tests

Run the full automated test suite (42 tests):

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/ -v
```

All 42 tests will execute against an isolated temporary SQLite database and complete in under 1 second.

### 4. Starting the Backend Server

Start the FastAPI application with Uvicorn:

```bash
PYTHONPATH=backend backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The server will start at `http://127.0.0.1:8000`. The SQLite database (`leads.db`) will initialize automatically on startup.

---

## API Reference & Usage Guide

### Health Check
```bash
curl -X GET http://127.0.0.1:8000/health
```
**Response:**
```json
{
  "status": "healthy",
  "service": "Ava Inbound Voice Agent",
  "version": "1.0.0",
  "environment": "development",
  "llm_mode": "deterministic_fallback"
}
```

---

### Step 1: Create a Session
```bash
curl -X POST http://127.0.0.1:8000/api/sessions
```
**Response:**
```json
{
  "session_id": "sess_8461159baa48",
  "state": "GREETING",
  "status": "active",
  "greeting": "Hello! I'm Ava, an AI assistant with the digital marketing agency. I can ask you a few quick questions to understand your business needs. Is now a good time?"
}
```

---

### Step 2: Submit Conversation Turns
Send the caller's responses with unique `turn_id` values:

#### Turn 1 — Agreement
```bash
curl -X POST http://127.0.0.1:8000/api/sessions/sess_8461159baa48/turns \
  -H "Content-Type: application/json" \
  -d '{
    "turn_id": "turn_1",
    "transcript": "Yes, now is a good time."
  }'
```
**Response:**
```json
{
  "session_id": "sess_8461159baa48",
  "turn_id": "turn_1",
  "intent": "lead_qualification",
  "conversation_state": "ASK_COMPANY",
  "response": "Could you briefly tell me your company name and what your business does?",
  "lead": {
    "company_name": null,
    "business_type": null,
    "company_size": null,
    "marketing_budget": null,
    "budget_currency": null,
    "budget_period": "unknown",
    "contact_name": null,
    "contact_email": null
  },
  "missing_fields": [
    "company_size",
    "marketing_budget",
    "budget_currency",
    "budget_period"
  ],
  "qualification_status": "in_progress",
  "should_end_call": false,
  "session_status": "active"
}
```

#### Turn 2 — Company Information
```bash
curl -X POST http://127.0.0.1:8000/api/sessions/sess_8461159baa48/turns \
  -H "Content-Type: application/json" \
  -d '{
    "turn_id": "turn_2",
    "transcript": "We run an e-commerce company called Acme Digital."
  }'
```
**Response:** Ava transitions to `ASK_SIZE` and asks: *"Thanks! Approximately how many employees or team members does your company have?"*

#### Turn 3 — Team Size
```bash
curl -X POST http://127.0.0.1:8000/api/sessions/sess_8461159baa48/turns \
  -H "Content-Type: application/json" \
  -d '{
    "turn_id": "turn_3",
    "transcript": "We have twenty-five employees."
  }'
```
**Response:** Ava transitions to `ASK_BUDGET` with `company_size = 25`.

#### Turn 4 — Marketing Budget
```bash
curl -X POST http://127.0.0.1:8000/api/sessions/sess_8461159baa48/turns \
  -H "Content-Type: application/json" \
  -d '{
    "turn_id": "turn_4",
    "transcript": "We spend ₹50,000 per month on marketing."
  }'
```
**Response:** Ava reaches `ENDED` state, saves the lead as `qualified`, and closes politely.

---

### Step 3: Inspect Session Transcript & Details
```bash
curl -X GET http://127.0.0.1:8000/api/sessions/sess_8461159baa48
```
Returns chronological transcript turns, current state, and captured lead data.

---

### Step 4: Query Persisted Leads
```bash
# List leads (reverse chronological order)
curl -X GET http://127.0.0.1:8000/api/leads

# Retrieve lead by lead_id
curl -X GET http://127.0.0.1:8000/api/leads/lead_1b3c74db64a1
```

---

## Phase 2 Integration Contract

Phase 2 will implement the browser-based voice interface. The exact integration points for Phase 2 are:

1. **Session Initialization:** `POST /api/sessions` on clicking "Start Call". The frontend immediately speaks the returned `greeting` via browser `SpeechSynthesis`.
2. **Turn Recognition Stream:** The browser Web Speech recognition captures speech and submits transcribed final utterances to `POST /api/sessions/{session_id}/turns`. The returned `response` string is queued for audio playback.
3. **Session Interruption & Manual Stop:** Clicking "End Call" calls `POST /api/sessions/{session_id}/end`, immediately cancelling synthesis.
4. **Lead Dashboard:** Connects to `GET /api/leads` and `GET /api/sessions/{session_id}` to render the live transcript and lead qualification card.
5. **CORS:** Pre-configured for `http://localhost:3000` and `http://127.0.0.1:3000`.

---

## Documentation Links

- [Architecture Document](docs/ARCHITECTURE.md)
- [State Machine Flowchart](docs/FLOWCHART.md)
- [Automated Test Execution Report](docs/TEST_RESULTS.md)
