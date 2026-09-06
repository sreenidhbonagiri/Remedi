"""Copilot REST surface: program catalog, PDF export, and agent triage."""

from __future__ import annotations

import io
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.medication import Medication
from app.models.program import Program
from app.schemas.agent import AgentTriageRequest, AgentTriageResponse
from app.schemas.application import ApplicationPDFRequest, ProgramOut
from app.services.copilot_agent import run_copilot_agent
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
    return (
        db.query(Program)
        .options(selectinload(Program.medications))
        .filter(Program.is_pap.is_(True))
        .order_by(Program.name)
        .all()
    )


@router.post("/agent/triage", response_model=AgentTriageResponse)
def triage_medication_request(
    payload: AgentTriageRequest,
    db: Session = Depends(get_db),
) -> AgentTriageResponse:
    result = run_copilot_agent(
        db,
        query=payload.query,
        annual_income=payload.annual_income,
        household_size=payload.household_size,
        state=payload.state,
        is_uninsured=payload.is_uninsured,
        is_medicare=payload.is_medicare,
    )
    raw = result.get("tool_results") or {}
    savings = json.loads(raw["find_medication_savings"]) if raw.get("find_medication_savings") else None
    fpl = json.loads(raw["evaluate_federal_poverty_level"]) if raw.get("evaluate_federal_poverty_level") else None
    return AgentTriageResponse(
        action_plan=result.get("action_plan") or "",
        medication_query=result.get("medication_query") or "",
        visited_nodes=list(result.get("visited_nodes") or []),
        savings=savings,
        fpl=fpl,
    )


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
