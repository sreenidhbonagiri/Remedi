from __future__ import annotations

from pydantic import BaseModel, Field


class AlternativeOut(BaseModel):
    name: str
    generic_name: str
    te_code: str
    cash_price: float | None = None
    brand_cash_price: float | None = None
    savings_amount: float | None = None
    savings_percent: float | None = None
    strength: str = ""
    form: str = ""
    ndc: str = ""


class EligibleProgramOut(BaseModel):
    name: str
    manufacturer: str
    fpl_limit_percent: float
    fpl_percent: float | None = None
    eligible: bool | None = None
    reason: str = ""
    phone: str = ""
    description: str = ""


class SavingsResponse(BaseModel):
    query_name: str
    matched_medication: str | None = None
    matched_generic_name: str | None = None
    brand_cash_price: float | None = None
    fpl_percent: float | None = None
    fpl_year: int = 2026
    household_size: int | None = None
    state: str = "PA"
    alternatives: list[AlternativeOut] = Field(default_factory=list)
    eligible_programs: list[EligibleProgramOut] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
