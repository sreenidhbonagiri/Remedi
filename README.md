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

## Executive Summary

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
