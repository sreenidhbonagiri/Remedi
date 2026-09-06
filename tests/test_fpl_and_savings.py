from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.fpl import (
    FPL_YEAR,
    fpl_limit_amount,
    fpl_percent,
    meets_threshold,
    poverty_guideline,
)
from app.services.savings_engine import find_savings_and_alternatives


def test_2026_fpl_contiguous_household_of_one() -> None:
    assert FPL_YEAR == 2026
    assert poverty_guideline(1, "PA") == 15960
    assert poverty_guideline(1, "IL") == 15960
    assert fpl_percent(35000, 1, "PA") == 219.3
    assert fpl_percent(35000, 1, "IL") == 219.3
    assert fpl_limit_amount(1, "PA", 400.0) == 63840.0
    assert meets_threshold(35000, 1, "PA", 400.0) is True
    assert meets_threshold(80000, 1, "PA", 400.0) is False


def test_2026_fpl_alaska_and_large_household() -> None:
    assert poverty_guideline(1, "AK") == 19950
    assert fpl_percent(35000, 1, "AK") == 175.4
    assert poverty_guideline(9, "PA") == 55720 + 5680


def test_humira_ab_generic_savings_math(db_session: Session) -> None:
    result = find_savings_and_alternatives(
        db_session,
        query_name="Humira",
        annual_income=35000,
        household_size=1,
        state="PA",
        is_uninsured=True,
        is_medicare=False,
    )
    assert result.matched_medication == "Humira"
    assert result.matched_generic_name.lower() == "adalimumab"
    assert result.brand_cash_price == 8000.0
    assert result.fpl_percent == 219.3
    assert result.alternatives, "expected an AB-rated adalimumab alternative"
    alt = next(item for item in result.alternatives if item.te_code == "AB")
    assert alt.cash_price == 1600.0
    assert alt.savings_amount == 6400.0
    assert alt.savings_percent == 80.0
    expected = round((8000.0 - 1600.0) / 8000.0 * 100.0, 1)
    assert alt.savings_percent == expected


def test_sitagliptin_query_matches_brand_and_generic(db_session: Session) -> None:
    result = find_savings_and_alternatives(db_session, query_name="sitagliptin")
    assert result.matched_medication == "Januvia"
    assert result.brand_cash_price == 580.0
    ab = [item for item in result.alternatives if item.te_code == "AB"]
    assert ab
    assert ab[0].savings_percent == 90.0
    assert ab[0].savings_amount == 522.0


def test_program_matching_400_vs_300_fpl_caps(db_session: Session) -> None:
    humira = find_savings_and_alternatives(
        db_session,
        query_name="Humira",
        annual_income=35000,
        household_size=1,
        state="PA",
        is_uninsured=True,
    )
    abbvie = next(p for p in humira.eligible_programs if p.name == "myAbbVie Assist")
    assert abbvie.fpl_limit_percent == 400.0
    assert abbvie.fpl_percent == 219.3
    assert abbvie.eligible is True

    nucala_ok = find_savings_and_alternatives(
        db_session,
        query_name="Nucala",
        annual_income=35000,
        household_size=1,
        state="PA",
        is_uninsured=True,
    )
    gsk_ok = next(p for p in nucala_ok.eligible_programs if p.name == "GSK For You")
    assert gsk_ok.fpl_limit_percent == 300.0
    assert gsk_ok.eligible is True

    nucala_over = find_savings_and_alternatives(
        db_session,
        query_name="Nucala",
        annual_income=55000,
        household_size=1,
        state="PA",
        is_uninsured=True,
    )
    assert fpl_percent(55000, 1, "PA") == 344.6
    gsk_over = next(p for p in nucala_over.eligible_programs if p.name == "GSK For You")
    assert gsk_over.eligible is False
    abbvie_still = find_savings_and_alternatives(
        db_session,
        query_name="Humira",
        annual_income=55000,
        household_size=1,
        state="PA",
    )
    assert next(p for p in abbvie_still.eligible_programs if p.name == "myAbbVie Assist").eligible is True


def test_medicare_is_not_pap_eligible(db_session: Session) -> None:
    result = find_savings_and_alternatives(
        db_session,
        query_name="Januvia",
        annual_income=20000,
        household_size=1,
        state="PA",
        is_uninsured=False,
        is_medicare=True,
    )
    assert result.eligible_programs
    assert all(program.eligible is False for program in result.eligible_programs)
    assert "Medicare" in result.eligible_programs[0].reason


def test_unknown_medication_returns_note(db_session: Session) -> None:
    result = find_savings_and_alternatives(db_session, query_name="Unobtainium XR")
    assert result.matched_medication is None
    assert result.alternatives == []
    assert any("Unobtainium XR" in note for note in result.notes)
