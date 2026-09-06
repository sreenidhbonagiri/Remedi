from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session, selectinload

from app.db.seed import AB_GENERICS, CATALOG_PROGRAM_NAME, PROGRAMS, seed_database
from app.models.medication import Medication
from app.models.program import Program
from app.services.openfda import parse_ndc_result, sync_ndc_to_medications, upsert_medication_from_ndc


def test_seed_creates_pap_programs_and_catalog(db_session: Session) -> None:
    paps = db_session.query(Program).filter(Program.is_pap.is_(True)).all()
    assert {program.name for program in paps} == {item["name"] for item in PROGRAMS}
    catalog = db_session.query(Program).filter(Program.name == CATALOG_PROGRAM_NAME).one()
    assert catalog.is_pap is False
    assert catalog.manufacturer == "FDA NDC Directory"


def test_seed_is_idempotent(db_session: Session) -> None:
    pap_count = db_session.query(Program).filter(Program.is_pap.is_(True)).count()
    med_count = db_session.query(Medication).count()
    seed_database(db_session)
    assert db_session.query(Program).filter(Program.is_pap.is_(True)).count() == pap_count
    assert db_session.query(Medication).count() == med_count


def test_humira_belongs_to_myabbvie_assist(db_session: Session) -> None:
    program = (
        db_session.query(Program)
        .options(selectinload(Program.medications))
        .filter(Program.name == "myAbbVie Assist")
        .one()
    )
    names = {med.name for med in program.medications}
    assert "Humira" in names
    humira = next(med for med in program.medications if med.name == "Humira")
    assert humira.generic_name.lower() == "adalimumab"
    assert humira.program_id == program.id
    assert humira.cash_price == 8000.0
    assert humira.program.name == "myAbbVie Assist"


def test_ab_generics_are_seeded_on_catalog(db_session: Session) -> None:
    catalog = db_session.query(Program).filter(Program.name == CATALOG_PROGRAM_NAME).one()
    generics = (
        db_session.query(Medication)
        .filter(Medication.program_id == catalog.id, Medication.te_code == "AB")
        .all()
    )
    seeded_names = {item["name"] for item in AB_GENERICS}
    assert seeded_names <= {med.name for med in generics}
    adalimumab = next(med for med in generics if med.name == "adalimumab")
    assert adalimumab.is_generic is True
    assert adalimumab.cash_price == 1600.0
    assert adalimumab.generic_name.lower() == "adalimumab"


def test_program_medication_relationship_round_trip(db_session: Session) -> None:
    januvia = db_session.query(Medication).filter(Medication.name == "Januvia").one()
    assert januvia.program.name == "Merck Patient Assistance Program"
    covered = {med.name for med in januvia.program.medications}
    assert "Januvia" in covered
    assert "Keytruda" in covered


def test_parse_ndc_brand_active_ingredient_form_strength() -> None:
    parsed = parse_ndc_result(
        {
            "product_ndc": "0074-3799",
            "brand_name": "HUMIRA",
            "generic_name": "ADALIMUMAB",
            "dosage_form": "INJECTION, SOLUTION",
            "active_ingredients": [{"name": "ADALIMUMAB", "strength": "40 mg/0.4 mL"}],
        }
    )
    assert parsed["name"] == "HUMIRA"
    assert parsed["generic_name"] == "ADALIMUMAB"
    assert parsed["form"] == "INJECTION, SOLUTION"
    assert parsed["strength"] == "40 mg/0.4 mL"
    assert parsed["ndc"] == "0074-3799"


def test_openfda_upsert_does_not_duplicate_humira(db_session: Session) -> None:
    catalog = db_session.query(Program).filter(Program.name == CATALOG_PROGRAM_NAME).one()
    before = db_session.query(Medication).filter(Medication.name == "Humira").count()
    parsed = parse_ndc_result(
        {
            "product_ndc": "0074-3799",
            "brand_name": "Humira",
            "dosage_form": "prefilled pen",
            "active_ingredient": [{"name": "adalimumab", "strength": "40 mg/0.4 mL"}],
        }
    )
    upsert_medication_from_ndc(db_session, parsed, catalog.id)
    db_session.commit()
    after = db_session.query(Medication).filter(Medication.name == "Humira").count()
    assert after == before == 1


def test_openfda_sync_inserts_new_product(db_session: Session, monkeypatch) -> None:
    async def fake_fetch(search=None, limit=30, client=None):
        return {
            "results": [
                {
                    "product_ndc": "9999-0001",
                    "brand_name": "Examplezumab",
                    "dosage_form": "TABLET",
                    "active_ingredients": [{"name": "examplezumab", "strength": "10 mg"}],
                }
            ]
        }

    monkeypatch.setattr("app.services.openfda.fetch_ndc_directory", fake_fetch)
    created = asyncio.run(sync_ndc_to_medications(db_session, search="examplezumab"))
    assert len(created) == 1
    row = db_session.query(Medication).filter(Medication.ndc == "9999-0001").one()
    assert row.name == "Examplezumab"
    assert row.generic_name.lower() == "examplezumab"
    assert row.form == "TABLET"
    assert row.strength == "10 mg"
    assert row.program.name == CATALOG_PROGRAM_NAME
