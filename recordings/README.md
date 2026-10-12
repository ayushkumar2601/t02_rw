# Demo Recording Guidelines & Submission Guide

This folder is designated for video recordings and demonstrations of the **Ava Autonomous Inbound Voice Agent**.

---

## 1. Demo Video Checklist

When recording the final walkthrough video for assignment submission (recommended 3–5 minutes), cover the following workflow:

- [ ] **1. Setup & Environment Overview**:
  - Show the backend running on `http://127.0.0.1:8000` (FastAPI, SQLite, 43 passing automated tests).
  - Show the frontend dashboard running on `http://localhost:3000` (Next.js 16).
  - Emphasize **₹0 implementation cost** with native browser Web Speech API and deterministic offline engine.

- [ ] **2. Live Voice Interaction (Happy Path)**:
  - Click **Start Voice Call**.
  - Listen to Ava's greeting: *"Hello! I'm Ava, an AI assistant with the digital marketing agency..."*
  - Answer naturally: *"Companies name is Tectrongo and the business is digital marketing."*
  - Verify that the **Extracted Lead Record** immediately reflects:
    - **Company Name**: `Tectrongo`
    - **Business Type / Industry**: `Digital Marketing`
  - Answer employee count: *"We have 15 team members."*
  - Answer budget: *"Our budget is 50,000 rupees a month."*
  - Watch Ava wrap up the call politely and finalize the session.

- [ ] **3. Acoustic Echo Mitigation & Half-Duplex Turn Taking**:
  - Show that when using laptop speakers without headphones, Ava's spoken words are not captured as caller utterances due to:
    - Automatic mic muting during Ava's speech synthesis.
    - Post-speech acoustic dissipation cooldown (600ms).
    - Multi-layer transcript echo suppression filter.
  - Demonstrate the **Interrupt Ava** button to safely cut Ava off and speak immediately.

- [ ] **4. Text Fallback & Resilience**:
  - Demonstrate typing an answer or correction in the inline text fallback input.
  - Show how corrections (e.g. *"Actually make that 25 employees"*) cleanly update the record.

- [ ] **5. Persistence & Verification**:
  - Scroll down to the **Saved Leads in Database (SQLite)** table.
  - Confirm the lead row is persisted with `lead_id`, `company_name`, `business_type`, `company_size`, `marketing_budget`, `qualification_status: qualified`, and timestamp.

---

## 2. File Organization

Save your screen recording in this directory:
- `recordings/ava_voice_agent_demo.mp4` (or `.webm`)
- Optionally provide a public Loom or Google Drive link in your submission notes if file sizes exceed repository limits.
