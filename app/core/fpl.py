"""2026 HHS Federal Poverty Guidelines (effective January 13, 2026).

Source: 91 FR 1797 (January 15, 2026), 42 U.S.C. 9902(2).
"""

from __future__ import annotations

from typing import Literal

FPL_YEAR = 2026

GuidelineRegion = Literal["contiguous", "AK", "HI"]

# Base amounts for household sizes 1–8, plus the per-person increment thereafter.
_GUIDELINES: dict[GuidelineRegion, tuple[list[int], int]] = {
    "contiguous": (
        [15960, 21640, 27320, 33000, 38680, 44360, 50040, 55720],
        5680,
    ),
    "AK": (
        [19950, 27050, 34150, 41250, 48350, 55450, 62550, 69650],
        7100,
    ),
    "HI": (
        [18360, 24890, 31420, 37950, 44480, 51010, 57540, 64070],
        6530,
    ),
}


def guideline_region(state: str) -> GuidelineRegion:
    code = (state or "").strip().upper()
    if code in {"AK", "ALASKA"}:
        return "AK"
    if code in {"HI", "HAWAII"}:
        return "HI"
    return "contiguous"


def poverty_guideline(household_size: int, state: str = "") -> int:
    """Return the 100% FPL annual dollar amount for a household and state."""
    if household_size < 1:
        raise ValueError("household_size must be at least 1")
    bases, increment = _GUIDELINES[guideline_region(state)]
    if household_size <= 8:
        return bases[household_size - 1]
    return bases[7] + (household_size - 8) * increment


def fpl_percent(annual_income: float, household_size: int, state: str = "") -> float:
    """Gross annual income as a percentage of the applicable 2026 FPL, one decimal."""
    guideline = poverty_guideline(household_size, state)
    return round((float(annual_income) / guideline) * 100, 1)


def fpl_limit_amount(household_size: int, state: str = "", limit_percent: float = 400.0) -> float:
    """Dollar cap at a given FPL multiple (e.g. 400% of poverty)."""
    return round(poverty_guideline(household_size, state) * (limit_percent / 100.0), 2)


def meets_threshold(
    annual_income: float,
    household_size: int,
    state: str = "",
    limit_percent: float = 400.0,
) -> bool:
    return fpl_percent(annual_income, household_size, state) <= limit_percent
