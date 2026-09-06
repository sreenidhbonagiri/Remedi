"""Cash-price savings versus AB-rated generics, plus PAP eligibility matching."""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.core import fpl as fpl_mod
from app.models.medication import Medication
from app.models.program import Program
from app.schemas.savings import AlternativeOut, EligibleProgramOut, SavingsResponse

AB_CODE = "AB"


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _query_medications(db: Session, query_name: str) -> list[Medication]:
    needle = query_name.strip()
    if not needle:
        return []
    lowered = needle.lower()
    return (
        db.query(Medication)
        .options(selectinload(Medication.program))
        .filter(
            or_(
                func.lower(Medication.name) == lowered,
                func.lower(Medication.generic_name) == lowered,
                Medication.name.ilike(f"%{needle}%"),
                Medication.generic_name.ilike(f"%{needle}%"),
            )
        )
        .all()
    )


def _pick_reference(matches: list[Medication], query_name: str) -> Medication | None:
    if not matches:
        return None
    lowered = _norm(query_name)
    brands = [row for row in matches if not row.is_generic]
    priced_brands = [row for row in brands if row.cash_price]
    if priced_brands:
        exact_brand = [row for row in priced_brands if _norm(row.name) == lowered]
        return max(exact_brand or priced_brands, key=lambda row: row.cash_price or 0.0)
    exact_name = [row for row in matches if _norm(row.name) == lowered]
    if exact_name:
        return exact_name[0]
    return max(matches, key=lambda row: row.cash_price or 0.0)


def _ab_alternatives(db: Session, reference: Medication) -> list[Medication]:
    ingredient = _norm(reference.generic_name) or _norm(reference.name)
    if not ingredient:
        return []
    rows = (
        db.query(Medication)
        .filter(
            func.lower(Medication.generic_name) == ingredient,
            func.upper(Medication.te_code) == AB_CODE,
            Medication.id != reference.id,
        )
        .all()
    )
    return rows


def _savings_for(reference: Medication, generic: Medication) -> AlternativeOut:
    brand_price = reference.cash_price
    generic_price = generic.cash_price
    amount = None
    percent = None
    if brand_price is not None and generic_price is not None:
        amount = round(float(brand_price) - float(generic_price), 2)
        if float(brand_price) > 0 and amount > 0:
            percent = round((amount / float(brand_price)) * 100.0, 1)
        elif amount <= 0:
            percent = 0.0
    return AlternativeOut(
        name=generic.name,
        generic_name=generic.generic_name,
        te_code=(generic.te_code or AB_CODE).upper(),
        cash_price=generic_price,
        brand_cash_price=brand_price,
        savings_amount=amount,
        savings_percent=percent,
        strength=generic.strength,
        form=generic.form,
        ndc=generic.ndc or "",
    )


def _program_reason(
    *,
    eligible: bool | None,
    fpl_value: float | None,
    limit: float,
    is_uninsured: bool,
    is_medicare: bool,
) -> str:
    if is_medicare:
        return "Manufacturer PAPs typically exclude Medicare beneficiaries."
    if eligible is None:
        return "Income and household size are required to score 2026 FPL eligibility."
    if not is_uninsured:
        prefix = "Patient reported insurance coverage. "
    else:
        prefix = ""
    if eligible:
        return f"{prefix}Household FPL {fpl_value}% is at or below the {limit}% program cap."
    return f"{prefix}Household FPL {fpl_value}% exceeds the {limit}% program cap."


def find_savings_and_alternatives(
    db: Session,
    query_name: str,
    annual_income: float | None = None,
    household_size: int | None = None,
    state: str = "PA",
    is_uninsured: bool = True,
    is_medicare: bool = False,
) -> SavingsResponse:
    matches = _query_medications(db, query_name)
    fpl_value = None
    if annual_income is not None and household_size:
        fpl_value = fpl_mod.fpl_percent(annual_income, household_size, state)

    if not matches:
        return SavingsResponse(
            query_name=query_name,
            fpl_percent=fpl_value,
            fpl_year=fpl_mod.FPL_YEAR,
            household_size=household_size,
            state=state,
            notes=[f"No medication matching '{query_name}' was found in the local catalog."],
        )

    reference = _pick_reference(matches, query_name)
    assert reference is not None
    ingredient = reference.generic_name or reference.name
    alternatives = [_savings_for(reference, generic) for generic in _ab_alternatives(db, reference)]
    alternatives.sort(key=lambda item: item.savings_percent or 0.0, reverse=True)

    program_rows = (
        db.query(Program)
        .options(selectinload(Program.medications))
        .join(Medication)
        .filter(
            Program.is_pap.is_(True),
            or_(
                func.lower(Medication.name) == _norm(reference.name),
                func.lower(Medication.generic_name) == _norm(ingredient),
            ),
        )
        .distinct()
        .all()
    )

    eligible_programs: list[EligibleProgramOut] = []
    for program in program_rows:
        eligible: bool | None
        if is_medicare:
            eligible = False
        elif fpl_value is None:
            eligible = None
        else:
            eligible = fpl_value <= program.fpl_limit_percent
        eligible_programs.append(
            EligibleProgramOut(
                name=program.name,
                manufacturer=program.manufacturer,
                fpl_limit_percent=program.fpl_limit_percent,
                fpl_percent=fpl_value,
                eligible=eligible,
                reason=_program_reason(
                    eligible=eligible,
                    fpl_value=fpl_value,
                    limit=program.fpl_limit_percent,
                    is_uninsured=is_uninsured,
                    is_medicare=is_medicare,
                ),
                phone=program.phone,
                description=program.description,
            )
        )

    notes: list[str] = []
    if not alternatives:
        notes.append("No AB-rated generic alternatives with a catalog cash price were found for this product.")
    if not eligible_programs:
        notes.append("No manufacturer patient assistance program in the catalog covers this product.")

    return SavingsResponse(
        query_name=query_name,
        matched_medication=reference.name,
        matched_generic_name=ingredient,
        brand_cash_price=reference.cash_price,
        fpl_percent=fpl_value,
        fpl_year=fpl_mod.FPL_YEAR,
        household_size=household_size,
        state=state,
        alternatives=alternatives,
        eligible_programs=eligible_programs,
        notes=notes,
    )
