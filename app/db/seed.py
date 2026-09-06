"""Seed manufacturer assistance programs and covered medications."""

from sqlalchemy.orm import Session

from app.models.medication import Medication
from app.models.program import Program

CATALOG_PROGRAM_NAME = "National Drug Catalog"

# Monthly cash-pay list prices used by the savings engine (deterministic fixtures).
BRAND_CASH_PRICES: dict[str, float] = {
    "Humira": 8000.00,
    "Skyrizi": 18000.00,
    "Rinvoq": 6200.00,
    "Mavyret": 13100.00,
    "Linzess": 540.00,
    "Trulicity": 973.00,
    "Mounjaro": 1069.00,
    "Taltz": 6500.00,
    "Januvia": 580.00,
    "Keytruda": 11000.00,
    "Nucala": 3400.00,
    "Trelegy Ellipta": 650.00,
}

AB_GENERICS = [
    {
        "name": "adalimumab",
        "generic_name": "adalimumab",
        "strength": "40 mg/0.4 mL",
        "form": "prefilled pen",
        "ndc": "61314-0327",
        "cash_price": 1600.00,
        "te_code": "AB",
        "is_generic": True,
    },
    {
        "name": "sitagliptin",
        "generic_name": "sitagliptin",
        "strength": "100 mg",
        "form": "tablet",
        "ndc": "00093-5756",
        "cash_price": 58.00,
        "te_code": "AB",
        "is_generic": True,
    },
    {
        "name": "linaclotide",
        "generic_name": "linaclotide",
        "strength": "145 mcg",
        "form": "capsule",
        "ndc": "68180-0714",
        "cash_price": 162.00,
        "te_code": "AB",
        "is_generic": True,
    },
]

PROGRAMS = [
    {
        "name": "myAbbVie Assist",
        "manufacturer": "AbbVie",
        "fpl_limit_percent": 400.0,
        "description": (
            "Free AbbVie medicines for qualifying U.S. patients with limited or no "
            "coverage who demonstrate financial need at or below 400% of the Federal "
            "Poverty Level."
        ),
        "phone": "1-800-222-6885",
        "mailing_address": "myAbbVie Assist, P.O. Box 220608, Charlotte, NC 28222",
        "medications": [
            {
                "name": "Humira",
                "generic_name": "adalimumab",
                "strength": "40 mg/0.4 mL",
                "form": "prefilled pen",
                "ndc": "0074-3799",
                "cash_price": 8000.00,
            },
            {
                "name": "Skyrizi",
                "generic_name": "risankizumab-rzaa",
                "strength": "150 mg/mL",
                "form": "prefilled pen",
                "ndc": "0074-2042",
                "cash_price": 18000.00,
            },
            {
                "name": "Rinvoq",
                "generic_name": "upadacitinib",
                "strength": "15 mg",
                "form": "extended-release tablet",
                "ndc": "0074-2306",
                "cash_price": 6200.00,
            },
            {
                "name": "Mavyret",
                "generic_name": "glecaprevir/pibrentasvir",
                "strength": "100 mg/40 mg",
                "form": "tablet",
                "ndc": "0074-2625",
                "cash_price": 13100.00,
            },
            {
                "name": "Linzess",
                "generic_name": "linaclotide",
                "strength": "145 mcg",
                "form": "capsule",
                "ndc": "0456-1201",
                "cash_price": 540.00,
            },
        ],
    },
    {
        "name": "Lilly Cares Foundation",
        "manufacturer": "Eli Lilly and Company",
        "fpl_limit_percent": 400.0,
        "description": "Patient assistance for qualifying Lilly medicines, typically at or below 400% FPL.",
        "phone": "1-800-545-6962",
        "mailing_address": "Lilly Cares Foundation, P.O. Box 230999, Centreville, VA 20120",
        "medications": [
            {
                "name": "Trulicity",
                "generic_name": "dulaglutide",
                "strength": "1.5 mg/0.5 mL",
                "form": "pen injector",
                "ndc": "0002-1433",
                "cash_price": 973.00,
            },
            {
                "name": "Mounjaro",
                "generic_name": "tirzepatide",
                "strength": "5 mg/0.5 mL",
                "form": "pen injector",
                "ndc": "0002-1506",
                "cash_price": 1069.00,
            },
            {
                "name": "Taltz",
                "generic_name": "ixekizumab",
                "strength": "80 mg/mL",
                "form": "autoinjector",
                "ndc": "0002-1445",
                "cash_price": 6500.00,
            },
        ],
    },
    {
        "name": "Merck Patient Assistance Program",
        "manufacturer": "Merck & Co.",
        "fpl_limit_percent": 400.0,
        "description": "No-cost Merck medicines for eligible uninsured or underinsured patients.",
        "phone": "1-800-727-5400",
        "mailing_address": "Merck Patient Assistance Program, P.O. Box 690, Horsham, PA 19044",
        "medications": [
            {
                "name": "Januvia",
                "generic_name": "sitagliptin",
                "strength": "100 mg",
                "form": "tablet",
                "ndc": "0006-0277",
                "cash_price": 580.00,
            },
            {
                "name": "Keytruda",
                "generic_name": "pembrolizumab",
                "strength": "100 mg/4 mL",
                "form": "injection",
                "ndc": "0006-3026",
                "cash_price": 11000.00,
            },
        ],
    },
    {
        "name": "GSK For You",
        "manufacturer": "GSK",
        "fpl_limit_percent": 300.0,
        "description": "GSK patient assistance for qualifying specialty and respiratory medicines.",
        "phone": "1-866-728-4368",
        "mailing_address": "GSK For You, P.O. Box 220590, Charlotte, NC 28222",
        "medications": [
            {
                "name": "Nucala",
                "generic_name": "mepolizumab",
                "strength": "100 mg",
                "form": "injection",
                "ndc": "0173-0881",
                "cash_price": 3400.00,
            },
            {
                "name": "Trelegy Ellipta",
                "generic_name": "fluticasone/umeclidinium/vilanterol",
                "strength": "100/62.5/25 mcg",
                "form": "inhaler",
                "ndc": "0173-0887",
                "cash_price": 650.00,
            },
        ],
    },
]


def _ensure_catalog_program(db: Session) -> Program:
    program = db.query(Program).filter(Program.name == CATALOG_PROGRAM_NAME).one_or_none()
    if program is None:
        program = Program(
            name=CATALOG_PROGRAM_NAME,
            manufacturer="FDA NDC Directory",
            fpl_limit_percent=0.0,
            is_pap=False,
            description=(
                "Reference listing of FDA-listed products used for cash-price and "
                "AB-rated bioequivalence comparison. Not a patient assistance program."
            ),
            phone="",
            mailing_address="",
        )
        db.add(program)
        db.flush()
    return program


def _medication_exists(db: Session, name: str, strength: str) -> bool:
    return (
        db.query(Medication)
        .filter(Medication.name == name, Medication.strength == strength)
        .count()
        > 0
    )


def _backfill_brand_prices(db: Session) -> None:
    for medication in db.query(Medication).all():
        listed = BRAND_CASH_PRICES.get(medication.name)
        if listed is not None and medication.cash_price is None:
            medication.cash_price = listed


def seed_database(db: Session) -> None:
    if db.query(Program).filter(Program.is_pap.is_(True)).count() == 0:
        for program_data in PROGRAMS:
            payload = dict(program_data)
            medications = payload.pop("medications")
            program = Program(**payload)
            db.add(program)
            db.flush()
            for med in medications:
                db.add(Medication(program_id=program.id, **med))

    catalog = _ensure_catalog_program(db)
    for generic in AB_GENERICS:
        if not _medication_exists(db, generic["name"], generic["strength"]):
            db.add(Medication(program_id=catalog.id, **generic))
    _backfill_brand_prices(db)
    db.commit()
