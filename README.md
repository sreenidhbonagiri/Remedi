# Patient Assistance Copilot — PDF Application Generator

Phase 5 of the copilot: an in-memory PDF generator and streaming export API for manufacturer Patient Assistance Program (PAP) applications.

The service scores household income against the **2026 HHS Federal Poverty Guidelines** (91 FR 1797), validates that the named program and medication exist in the catalog, and returns a 1–2 page official-format application packet.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8765
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). Fill in a patient, choose a seeded program (for example **myAbbVie Assist** / **Humira**), and download `assistance_application.pdf`.

Interactive API docs: [http://127.0.0.1:8765/docs](http://127.0.0.1:8765/docs).

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

A `$35,000` income for a household of one in Illinois is **219.3% FPL** against the 2026 contiguous-states guideline of `$15,960`, which is under the typical 400% PAP ceiling.

## Catalog

`GET /api/v1/programs` returns seeded manufacturer programs and covered drugs, including myAbbVie Assist, Lilly Cares Foundation, Merck Patient Assistance Program, and GSK For You.

## Tests

```bash
pytest tests/test_pdf_service.py -v
```

The suite checks page count and extracted text (patient name, drug name, calculated FPL) via PyPDF, and asserts the FastAPI endpoint returns HTTP 200 with the PDF download headers.

## Layout of this repo

- `app/services/pdf_generator.py` — ReportLab template (`generate_assistance_pdf`)
- `app/api/v1/copilot.py` — REST surface
- `app/core/fpl.py` — 2026 HHS poverty guidelines (contiguous, Alaska, Hawaii)
- `tests/test_pdf_service.py` — PDF and endpoint tests
