"""Copilot REST surface: program catalog and PDF application export."""

from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.medication import Medication
from app.models.program import Program
from app.schemas.application import ApplicationPDFRequest, ProgramOut
from app.services.pdf_generator import generate_assistance_pdf

router = APIRouter()


def _find_program(db: Session, name: str) -> Program | None:
    return (
        db.query(Program)
        .options(selectinload(Program.medications))
        .filter(func.lower(Program.name) == name.strip().lower())
        .one_or_none()
    )


def _find_medication(db: Session, name: str, program_id: int | None = None) -> Medication | None:
    query = db.query(Medication).filter(func.lower(Medication.name) == name.strip().lower())
    if program_id is not None:
        query = query.filter(Medication.program_id == program_id)
    return query.one_or_none()


@router.get("/programs", response_model=list[ProgramOut])
def list_programs(db: Session = Depends(get_db)) -> list[Program]:
    return db.query(Program).options(selectinload(Program.medications)).order_by(Program.name).all()


@router.post("/applications/generate-pdf")
def generate_application_pdf(
    payload: ApplicationPDFRequest,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    program = _find_program(db, payload.program_name)
    if program is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program not found: {payload.program_name}",
        )

    medication = _find_medication(db, payload.medication_name, program_id=program.id)
    if medication is None:
        # Still 404 if the drug exists elsewhere — callers must name a covered pair.
        any_med = _find_medication(db, payload.medication_name)
        if any_med is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Medication not found: {payload.medication_name}",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{payload.medication_name} is not covered by {program.name}.",
        )

    patient_data = {
        "patient_name": payload.patient_name,
        "annual_income": payload.annual_income,
        "household_size": payload.household_size,
        "state": payload.state,
        "is_uninsured": payload.is_uninsured,
        "strength": medication.strength,
        "generic_name": medication.generic_name,
        "form": medication.form,
        "fpl_limit_percent": program.fpl_limit_percent,
        "manufacturer": program.manufacturer,
        "program_phone": program.phone,
        "mailing_address": program.mailing_address,
    }
    pdf_bytes = generate_assistance_pdf(
        patient_data=patient_data,
        program_name=program.name,
        medication_name=medication.name,
    )
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="assistance_application.pdf"'},
    )
