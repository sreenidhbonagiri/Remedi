# Affordable Medication Sourcing Copilot

A FastAPI copilot that scores household income against the **2026 HHS Federal Poverty Guidelines** (91 FR 1797), compares brand cash prices to FDA **AB-rated** generics, triages next steps with a LangGraph agent, and exports manufacturer Patient Assistance Program (PAP) applications as PDFs.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8765
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). Use **Sourcing copilot** to triage a drug such as Humira, then generate `assistance_application.pdf` from a matching PAP.

Interactive API docs: [http://127.0.0.1:8765/docs](http://127.0.0.1:8765/docs).

No OpenAI key is required. When `OPENAI_API_KEY` is unset, the agent uses a deterministic string template that only interpolates tool JSON (cash prices, FPL percentages, and eligibility caps). Set the key to optionally use an LLM for extraction and synthesis; the same guardrail still applies.

## Agent triage

`POST /api/v1/agent/triage`

```json
{
  "query": "I take Humira, earn $35000, household of 1 in PA, uninsured.",
  "annual_income": 35000,
  "household_size": 1,
  "state": "PA",
  "is_uninsured": true,
  "is_medicare": false
}
```

The compiled LangGraph workflow is `extract_and_triage → execute_tools → synthesize_action_plan`. Tools wrap `app/services/savings_engine.py` and `app/core/fpl.py` and return JSON strings. A `$35,000` income for a household of one in Pennsylvania is **219.3% FPL** against the 2026 contiguous-states guideline of `$15,960`. Humira’s seeded cash price of `$8,000` versus AB-rated adalimumab at `$1,600` is **80.0%** savings.

## Generate a PDF

`POST /api/v1/applications/generate-pdf`

```json
{
  "patient_name": "Maria Chen",
  "medication_name": "Humira",
  "annual_income": 35000,
  "household_size": 1,
  "state": "IL",
  "is_uninsured": true,
  "program_name": "myAbbVie Assist"
}
```

The response is a `StreamingResponse` (`application/pdf`) with

`Content-Disposition: attachment; filename="assistance_application.pdf"`.

The PDF is built in an `io.BytesIO` buffer. Nothing is written to disk.

## Catalog

`GET /api/v1/programs` returns seeded manufacturer PAPs and covered drugs, including myAbbVie Assist, Lilly Cares Foundation, Merck Patient Assistance Program, and GSK For You. AB-rated cash-pay comparators live in an internal National Drug Catalog and are not listed as assistance programs.

## Tests

```bash
python3 -m pytest -v
```

- `tests/test_pdf_service.py` — PDF page count, extracted text, and download headers
- `tests/test_fpl_and_savings.py` — 2026 FPL math, PAP matching, AB generic savings
- `tests/test_copilot_agent.py` — tool JSON, graph transitions, numeric guardrail
- `tests/test_seeder_and_db.py` — program/medication relationships and openFDA upserts

## Layout of this repo

- `app/services/copilot_agent.py` — compiled LangGraph workflow
- `app/services/agent_tools.py` — LangChain tools for savings and FPL
- `app/services/savings_engine.py` — cash-price deltas versus AB generics
- `app/services/openfda.py` — async openFDA NDC client and safe upserts
- `app/services/pdf_generator.py` — ReportLab PAP application template
- `app/api/v1/copilot.py` — REST surface (catalog, PDF, agent triage)
- `app/core/fpl.py` — 2026 HHS poverty guidelines (contiguous, Alaska, Hawaii)
- `tests/` — PDF, FPL/savings, agent, and seeder suites
