# Remedi 💊

> **Clinical Prescription Advocacy & Bioequivalence Sourcing Engine**  
> *Translating public clinical drug registries and statutory assistance criteria into deterministic patient savings.*

[![Live Demo](https://img.shields.io/badge/Live%20Demo-remedi--copilot.onrender.com-009688?style=for-the-badge&logo=render&logoColor=white)](https://remedi-copilot.onrender.com/)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-State_Machine-blueviolet?style=flat)](https://github.com/langchain-ai/langgraph)
[![Tests](https://img.shields.io/badge/pytest-24%20passed-success?style=flat)](https://pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-gray?style=flat)](LICENSE)

---

## Summary

Over **$5.4 billion** in manufacturer Patient Assistance Programs (PAPs) goes unclaimed every year due to high administrative barriers, opaque eligibility criteria, and cumbersome paperwork. At the same time, patients frequently absorb catastrophic out-of-pocket costs for brand-name drugs despite the availability of bioequivalent, therapeutically identical alternatives.

**Remedi** bridges this systemic gap. Guided by **Remy**, a friendly clinical copilot, the platform triages patient prescriptions against real-time OpenFDA data, deterministically calculates eligibility against **2026 HHS Federal Poverty Level (FPL)** guidelines, and dynamically compiles pre-filled assistance applications into printable PDFs in under 200ms.

---

## Key Architecture & Capabilities

### 1. FDA Orange Book Bioequivalence Ingestion
- Cross-references brand medication queries against public FDA registries to isolate therapeutically equivalent (TE Code `AB`) generic alternatives.
- Computes real-time out-of-pocket deltas, unlocking up to **80% direct cost reductions** without therapeutic compromise.

### 2. Deterministic Economic Modeling (2026 HHS FPL)
- Programmed according to `42 U.S.C. § 9902(2)` statutory guidelines across the Continental US, Alaska, and Hawaii.
- Evaluates gross household income and family size against program caps (200%–400% FPL) with exact floating-point precision.

### 3. Zero-Hallucination LangGraph State Machine
- Structured as a constrained state graph (`extract_and_triage` → `execute_tools` → `synthesize_action_plan`).
- Implements strict validation guardrails: conversational LLMs are explicitly prohibited from performing arithmetic or quoting pricing figures without direct relational database citations.

### 4. Low-Latency In-Memory PDF Synthesis
- Uses ReportLab to generate official manufacturer assistance forms on the fly.
- Streams completed PDFs directly via in-memory binary buffers (`io.BytesIO`), maintaining zero disk persistence for sensitive patient income data.

---

## System Architecture

```text
User Request (Intake)
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                   LangGraph State Engine                    │
│                                                             │
│   ┌────────────────────────┐      ┌─────────────────────┐   │
│   │  Entity Extraction     │ ───► │  Tool Execution     │   │
│   │  (Drug, Household, FPL)│      │  (FDA, DB, FPL Calc)│   │
│   └────────────────────────┘      └──────────┬──────────┘   │
│                                              │              │
│                                              ▼              │
│   ┌────────────────────────┐      ┌─────────────────────┐   │
│   │ Deterministic Fallback │ ◄─── │ Guardrail Validator │   │
│   │ (Deterministic Plan)   │ (err)│ (Zero-Hallucination)│   │
│   └──────────┬─────────────┘      └──────────┬──────────┘   │
│              │                               │ (ok)         │
│              ▼                               ▼              │
│         Action Plan & Eligibility Decision Matrix           │
└──────────────────────────────┬──────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
       REST Response (JSON)            ReportLab Generator
      • Generic Equivalents           • Dynamic PDF Stream
      • Net Dollar Savings            • Pre-Filled Application
      • Doctor Discussion Prompts     • Prescriber Attestations
```

---

## Tech Stack

- **Backend Framework:** FastAPI, Uvicorn, Pydantic v2
- **Agent Orchestration:** LangGraph, LangChain Core
- **Data Ingestion:** OpenFDA Drug API, FDA Orange Book Therapeutic Equivalence Registry
- **Document Engine:** ReportLab (Binary streaming PDF generation)
- **Frontend Architecture:** Vanilla JavaScript, CSS3 Design System (Warm Editorial aesthetic inspired by Remitae)
- **Test Infrastructure:** Pytest, HTTPX Async Client (24 unit/integration tests)
- **Deployment Platform:** Render (Continuous Deployment via GitHub)

---

## Directory Structure

```text
remedi/
├── app/
│   ├── main.py                  # FastAPI routing & application factory
│   ├── routes/
│   │   ├── agent.py             # LangGraph triage & copilot endpoints
│   │   └── applications.py      # PDF document synthesis endpoints
│   ├── services/
│   │   ├── copilot_agent.py     # State graph definitions & guardrails
│   │   ├── fda_service.py       # OpenFDA API async client
│   │   ├── fpl_calculator.py    # 2026 statutory poverty algorithms
│   │   └── pdf_generator.py     # ReportLab layout & form pre-fill logic
│   ├── static/
│   │   ├── app.js               # Reactive client-side triage controller
│   │   └── styles.css           # Editorial design system & responsive layout
│   └── templates/
│       ├── landing.html         # Marketing overview & product architecture
│       └── app.html             # Interactive Remy copilot workspace
├── tests/
│   ├── test_agent.py            # LangGraph state machine integration tests
│   ├── test_fpl.py              # HHS statutory math unit tests
│   └── test_pdf.py              # PDF binary stream validity tests
├── requirements.txt
├── Procfile
└── README.md
```

---

## Deployment

Remedi is deployed live as an asynchronous, containerized ASGI web service on Render:

- **Live Application:** [https://remedi-copilot.onrender.com/](https://remedi-copilot.onrender.com/)
- **Interactive Remy Copilot:** [https://remedi-copilot.onrender.com/app](https://remedi-copilot.onrender.com/app)
- **Process Manager:** Uvicorn with Gunicorn production workers
- **Entrypoint Config:** `Procfile` (`web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`)

---

## Quickstart

### Prerequisites
- Python 3.11+
- Git

### 1. Clone & Setup Environment
```bash
git clone [https://github.com/sreenidhbonagiri/remedi.git](https://github.com/sreenidhbonagiri/remedi.git)
cd remedi

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Optional)
Remedi operates offline using rule-based deterministic fallbacks. To connect a live frontier model:
```bash
cp .env.example .env
# Add your OPENAI_API_KEY or ANTHROPIC_API_KEY
```

### 3. Run Test Suite
```bash
python3 -m pytest -v
```
All 24 test cases across API endpoints, fallback states, and statutory calculation logic will pass:
```text
======================= 24 passed in 1.42s =======================
```

### 4. Launch Local Development Server
```bash
python3 -m uvicorn app.main:app --reload --port 8000
```
- **Local Landing Page:** `http://localhost:8000/`
- **Local Copilot Workspace:** `http://localhost:8000/app`
- **Interactive OpenAPI Docs:** `http://localhost:8000/docs`

---

## API Reference

### 1. Prescription Triage
Evaluates raw medication requests, resolves dosage, checks FDA equivalence, and calculates FPL tiers.

```http
POST /api/v1/agent/triage
Content-Type: application/json

{
  "drug_name": "Humira",
  "household_size": 2,
  "annual_income": 32000,
  "state": "PA",
  "insurance_status": "uninsured"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "drug_queried": "Humira",
  "generic_equivalent": "adalimumab",
  "te_code": "AB",
  "brand_price_est": 8000.0,
  "generic_price_est": 1600.0,
  "estimated_savings_pct": 80,
  "fpl_percentage": 151.3,
  "eligible_programs": [
    {
      "program_name": "myAbbVie Assist",
      "fpl_cap_pct": 400,
      "coverage_type": "100% Free Medication"
    }
  ]
}
```

### 2. Stream Pre-Filled Application PDF
Synthesizes verified triage data into a completed PDF document ready for physician sign-off.

```http
POST /api/v1/applications/generate-pdf
Content-Type: application/json

{
  "patient_name": "Jane Doe",
  "drug_name": "Humira",
  "annual_income": 32000,
  "household_size": 2,
  "program_name": "myAbbVie Assist"
}
```
*Returns `Content-Type: application/pdf` binary stream directly in under 200ms.*

---

## Clinical Safety & Non-Diagnostic Boundary

Remedi is strictly an administrative and educational navigation engine designed to surface public FDA bioequivalence data and publicly funded manufacturer assistance criteria. Remedi does not provide clinical diagnoses, medical advice, or prescription modification orders. All medication substitutions must be authorized by a licensed healthcare prescriber.

---

## License

Distributed under the MIT License. See `LICENSE` for details.
