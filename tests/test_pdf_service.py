from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.core.fpl import fpl_percent
from app.services.pdf_generator import generate_assistance_pdf

SAMPLE_PATIENT = {
    "patient_name": "Maria Chen",
    "annual_income": 35000.0,
    "household_size": 1,
    "state": "IL",
    "is_uninsured": True,
    "strength": "40 mg/0.4 mL",
    "generic_name": "adalimumab",
    "form": "prefilled pen",
    "fpl_limit_percent": 400.0,
    "manufacturer": "AbbVie",
    "program_phone": "1-800-222-6885",
    "mailing_address": "myAbbVie Assist, P.O. Box 220608, Charlotte, NC 28222",
}


def _pdf_text(pdf_bytes: bytes) -> tuple[PdfReader, str]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return reader, text


def test_generate_assistance_pdf_in_memory_contains_patient_drug_and_fpl() -> None:
    pdf_bytes = generate_assistance_pdf(
        patient_data=SAMPLE_PATIENT,
        program_name="myAbbVie Assist",
        medication_name="Humira",
    )

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    # Generator must not spill a working file into the project tree.
    assert not Path("assistance_application.pdf").exists()

    reader, text = _pdf_text(pdf_bytes)
    assert len(reader.pages) >= 1

    expected_fpl = fpl_percent(
        SAMPLE_PATIENT["annual_income"],
        SAMPLE_PATIENT["household_size"],
        SAMPLE_PATIENT["state"],
    )
    assert expected_fpl == 219.3
    assert "Maria Chen" in text
    assert "Humira" in text
    assert f"{expected_fpl}% FPL" in text
    assert "400%" in text or "400% FPL" in text or "≤ 400%" in text


def test_generate_application_pdf_endpoint_streams_attachment(client: TestClient) -> None:
    response = client.post(
        "/api/v1/applications/generate-pdf",
        json={
            "patient_name": "Maria Chen",
            "medication_name": "Humira",
            "annual_income": 35000,
            "household_size": 1,
            "state": "IL",
            "is_uninsured": True,
            "program_name": "myAbbVie Assist",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    disposition = response.headers.get("content-disposition", "")
    assert 'attachment; filename="assistance_application.pdf"' in disposition
    assert response.content.startswith(b"%PDF")

    reader, text = _pdf_text(response.content)
    assert len(reader.pages) >= 1
    assert "Maria Chen" in text
    assert "Humira" in text
    assert "219.3% FPL" in text


def test_generate_application_pdf_unknown_program_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/applications/generate-pdf",
        json={
            "patient_name": "Maria Chen",
            "medication_name": "Humira",
            "annual_income": 35000,
            "household_size": 1,
            "state": "IL",
            "is_uninsured": True,
            "program_name": "Not A Real Program",
        },
    )
    assert response.status_code == 404
    assert "Program not found" in response.json()["detail"]


def test_generate_application_pdf_unknown_medication_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/applications/generate-pdf",
        json={
            "patient_name": "Maria Chen",
            "medication_name": "Unobtainium XR",
            "annual_income": 35000,
            "household_size": 1,
            "state": "IL",
            "is_uninsured": True,
            "program_name": "myAbbVie Assist",
        },
    )
    assert response.status_code == 404
    assert "Medication not found" in response.json()["detail"]
