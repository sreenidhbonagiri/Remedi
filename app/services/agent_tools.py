"""LangChain tools wrapping the savings engine and 2026 FPL helpers."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import BaseTool, tool
from sqlalchemy.orm import Session

from app.core import fpl as fpl_mod
from app.services.savings_engine import find_savings_and_alternatives


def fpl_snapshot(
    annual_income: float,
    household_size: int,
    state: str = "PA",
    limit_percent: float = 400.0,
) -> dict[str, Any]:
    guideline = fpl_mod.poverty_guideline(household_size, state)
    percent = fpl_mod.fpl_percent(annual_income, household_size, state)
    cap = fpl_mod.fpl_limit_amount(household_size, state, limit_percent)
    return {
        "fpl_year": fpl_mod.FPL_YEAR,
        "annual_income": float(annual_income),
        "household_size": int(household_size),
        "state": state,
        "region": fpl_mod.guideline_region(state),
        "guideline": guideline,
        "fpl_percent": percent,
        "limit_percent": float(limit_percent),
        "limit_amount": cap,
        "meets_threshold": fpl_mod.meets_threshold(
            annual_income, household_size, state, limit_percent
        ),
    }


def build_agent_tools(db: Session) -> list[BaseTool]:
    @tool
    def find_medication_savings(
        query_name: str,
        annual_income: float | None = None,
        household_size: int | None = None,
        state: str = "PA",
        is_uninsured: bool = True,
        is_medicare: bool = False,
    ) -> str:
        """Find cash-price savings versus FDA AB-rated generics and match manufacturer PAP eligibility using 2026 FPL."""
        result = find_savings_and_alternatives(
            db,
            query_name=query_name,
            annual_income=annual_income,
            household_size=household_size,
            state=state,
            is_uninsured=is_uninsured,
            is_medicare=is_medicare,
        )
        return result.model_dump_json()

    @tool
    def evaluate_federal_poverty_level(
        annual_income: float,
        household_size: int,
        state: str = "PA",
        limit_percent: float = 400.0,
    ) -> str:
        """Evaluate 2026 HHS Federal Poverty Guideline percentage, dollar cap, and threshold eligibility."""
        return json.dumps(fpl_snapshot(annual_income, household_size, state, limit_percent))

    return [find_medication_savings, evaluate_federal_poverty_level]
