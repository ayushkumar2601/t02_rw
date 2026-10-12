# State Machine Flowchart: Ava Inbound Voice Agent

This document visualizes the deterministic conversation state machine implemented in `backend/app/services/conversation_manager.py`.

---

## 1. Primary Qualification Flowchart

```mermaid
flowchart TD
    START([POST /api/sessions]) --> GREETING[GREETING<br/>Introduce Ava AI assistant]
    
    GREETING --> AGREE{Caller agrees<br/>to chat?}
    AGREE -- "No / Not interested" --> DECLINE[CLOSING<br/>Polite goodbye]
    DECLINE --> ENDED([ENDED<br/>Session completed])

    AGREE -- "Yes / Agrees" --> ASK_COMPANY[ASK_COMPANY<br/>Gather company name & business type]
    
    ASK_COMPANY --> ASK_SIZE[ASK_SIZE<br/>Gather approximate employee count]
    
    ASK_SIZE --> SIZE_CLEAR{Employee count<br/>clear?}
    SIZE_CLEAR -- "Ambiguous" --> CLARIFY_SIZE[CLARIFY_SIZE<br/>Clarify once: approximate team size]
    CLARIFY_SIZE --> ASK_BUDGET[ASK_BUDGET<br/>Gather marketing budget & period]
    SIZE_CLEAR -- "Clear integer" --> ASK_BUDGET
    
    ASK_BUDGET --> BUDGET_CLEAR{Budget, currency<br/>& period clear?}
    BUDGET_CLEAR -- "Ambiguous / Currency missing" --> CLARIFY_BUDGET[CLARIFY_BUDGET<br/>Clarify currency or billing period]
    CLARIFY_BUDGET --> VALIDATE_LEAD[VALIDATE_LEAD<br/>Recompute missing fields & qualification status]
    BUDGET_CLEAR -- "Clear or unknown" --> VALIDATE_LEAD
    
    VALIDATE_LEAD --> SAVE_LEAD[SAVE_LEAD<br/>Persist validated lead to SQLite]
    
    SAVE_LEAD --> SAVE_CHECK{SQLite save<br/>successful?}
    SAVE_CHECK -- "Yes" --> CLOSING_OK[CLOSING<br/>Summarize recorded details & next steps]
    SAVE_CHECK -- "No" --> CLOSING_FAIL[CLOSING<br/>Truthful failure fallback message]
    
    CLOSING_OK --> ENDED
    CLOSING_FAIL --> ENDED
```

---

## 2. Global Transition Hierarchy

The following global transitions apply from **every active conversation state**:

```mermaid
flowchart TD
    INBOUND_TURN[Inbound Turn: Caller Utterance] --> GLOBAL_CHECK{Evaluate Global<br/>Priority Rules}
    
    GLOBAL_CHECK -- "1. Intent: goodbye / Stop" --> GOODBYE_HANDLER[Transition to CLOSING<br/>Save available lead data<br/>Set should_end_call = true<br/>End session gracefully]
    
    GLOBAL_CHECK -- "2. Intent: human_request" --> HUMAN_HANDLER[Truthful disclosure: Cannot transfer<br/>Maintain current state<br/>Append pending qualification question]
    
    GLOBAL_CHECK -- "3. Intent: off_topic" --> OFFTOPIC_HANDLER[Brief polite acknowledgment<br/>Maintain current state<br/>Redirect to pending question]
    
    GLOBAL_CHECK -- "4. Intent: unclear" --> UNCLEAR_HANDLER[Prompt to repeat<br/>Maintain current state<br/>Re-ask active question]
    
    GLOBAL_CHECK -- "5. Caller correction<br/>(e.g., 'make that 40 employees')" --> CORRECTION_HANDLER[Update existing lead field<br/>Recalculate missing fields<br/>Preserve prior transcript turns]
    
    GLOBAL_CHECK -- "6. Provider Timeout / 429" --> FALLBACK_HANDLER[Trigger deterministic NLP fallback<br/>Preserve active session state<br/>Continue conversation without interruption]
    
    GLOBAL_CHECK -- "7. Normal qualification turn" --> STATE_MACHINE[Execute State-Specific Transition]
```

---

## 3. Plain English State Definitions

| State | Purpose | Next Transition on Success | Edge Cases Handled |
|---|---|---|---|
| `GREETING` | Ava introduces herself as an AI SDR and requests permission to ask quick questions. | `ASK_COMPANY` (caller agrees) | If caller declines or says not now, transitions directly to polite `CLOSING` and `ENDED`. |
| `ASK_COMPANY` | Inquires about company name and industry/business type. | `ASK_SIZE` | If caller prefers not to disclose, continues without blocking. |
| `ASK_SIZE` | Inquires about approximate number of team members or employees. | `ASK_BUDGET` (if clear count) | If count is ambiguous ("a few people"), transitions to `CLARIFY_SIZE`. |
| `CLARIFY_SIZE` | Asks focused clarification for approximate team size. | `ASK_BUDGET` | Permitted retry: 1 attempt. If still ambiguous, accepts `null` and continues. |
| `ASK_BUDGET` | Inquires about monthly/annual marketing budget. | `VALIDATE_LEAD` (if budget, currency, and period are clear) | If amount is given without currency or period, transitions to `CLARIFY_BUDGET`. If caller declines, leaves `null` and continues. |
| `CLARIFY_BUDGET` | Asks focused clarification on missing currency or timeframe without repeating known amounts. | `VALIDATE_LEAD` | Permitted retry: 1 attempt. Proceeds with available facts. |
| `VALIDATE_LEAD` | Server-side validation calculates `missing_fields` and determines `qualification_status`. | `SAVE_LEAD` | If required fields are satisfied, marks `qualified`. Otherwise marks `partially_qualified`. |
| `SAVE_LEAD` | Commits validated lead record into SQLite via `lead_repository`. | `CLOSING` | Prevents duplicate leads on retries; rolls back cleanly if write fails. |
| `CLOSING` | Delivers truthful closing message reflecting actual persistence state. Sets `should_end_call = true`. | `ENDED` | Never claims persistence succeeded unless confirmed by backend. |
| `ENDED` | Terminal state. | None | Rejects any subsequent turn submissions with HTTP 400. |

---

## 4. Browser Voice Interface & Half-Duplex Turn-Taking Loop

To prevent laptop speaker acoustic feedback and self-capture:

```mermaid
flowchart TD
    START([User clicks Start Voice Call]) --> SESS_CREATE[POST /api/sessions -> session_id]
    SESS_CREATE --> AVA_SPEAK[Ava Speaks Response<br/>SpeechSynthesisUtterance]
    
    subgraph Ava_Speaking [Speaker Protection Active]
        AVA_SPEAK --> PAUSE_MIC[Microphone Aborted<br/>isSpeaking = true<br/>UI: 'Ava speaking (Mic paused)']
        PAUSE_MIC --> INTERRUPT_CHECK{User clicks<br/>'Interrupt Ava'?}
        INTERRUPT_CHECK -- "Yes" --> CANCEL_SPEECH[window.speechSynthesis.cancel()<br/>Flush Hardware Audio Buffer]
        INTERRUPT_CHECK -- "No" --> WAIT_END[Speech Synthesis Completes]
    end

    CANCEL_SPEECH --> RESUME_MIC[Re-enable SpeechRecognition]
    WAIT_END --> COOLDOWN[Acoustic Dissipation Cooldown<br/>Wait 600ms for room echo to clear]
    COOLDOWN --> RESUME_MIC

    subgraph Caller_Speaking [Caller Turn Active]
        RESUME_MIC --> LISTEN[UI: 'Listening to you (Speak now)'<br/>SpeechRecognition listening]
        LISTEN --> TRANSCRIBE[Speech Transcript Produced]
        TRANSCRIBE --> ECHO_FILTER{isAcousticEcho?<br/>Does text match Ava's words?}
        ECHO_FILTER -- "Yes (Echo detected)" --> DISCARD[Discard Transcript<br/>Prevent False Turn]
        ECHO_FILTER -- "No (Genuine caller)" --> POST_TURN[POST /api/sessions/:id/turns]
    end

    POST_TURN --> PROCESS[Backend State Transition<br/>& Fact Extraction]
    PROCESS --> TERMINAL_CHECK{Call Ended?}
    TERMINAL_CHECK -- "No" --> AVA_SPEAK
    TERMINAL_CHECK -- "Yes" --> FINAL_SPEAK[Speak Final Farewell]
    FINAL_SPEAK --> CALL_END([Call Completed<br/>Lead Persisted in SQLite])
```

