"""Seed manufacturer assistance programs and covered medications."""

from sqlalchemy.orm import Session

from app.models.medication import Medication
from app.models.program import Program

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
            {"name": "Humira", "generic_name": "adalimumab", "strength": "40 mg/0.4 mL", "form": "prefilled pen"},
            {"name": "Skyrizi", "generic_name": "risankizumab-rzaa", "strength": "150 mg/mL", "form": "prefilled pen"},
            {"name": "Rinvoq", "generic_name": "upadacitinib", "strength": "15 mg", "form": "extended-release tablet"},
            {"name": "Mavyret", "generic_name": "glecaprevir/pibrentasvir", "strength": "100 mg/40 mg", "form": "tablet"},
            {"name": "Linzess", "generic_name": "linaclotide", "strength": "145 mcg", "form": "capsule"},
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
            {"name": "Trulicity", "generic_name": "dulaglutide", "strength": "1.5 mg/0.5 mL", "form": "pen injector"},
            {"name": "Mounjaro", "generic_name": "tirzepatide", "strength": "5 mg/0.5 mL", "form": "pen injector"},
            {"name": "Taltz", "generic_name": "ixekizumab", "strength": "80 mg/mL", "form": "autoinjector"},
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
            {"name": "Januvia", "generic_name": "sitagliptin", "strength": "100 mg", "form": "tablet"},
            {"name": "Keytruda", "generic_name": "pembrolizumab", "strength": "100 mg/4 mL", "form": "injection"},
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
            {"name": "Nucala", "generic_name": "mepolizumab", "strength": "100 mg", "form": "injection"},
            {"name": "Trelegy Ellipta", "generic_name": "fluticasone/umeclidinium/vilanterol", "strength": "100/62.5/25 mcg", "form": "inhaler"},
        ],
    },
]


def seed_database(db: Session) -> None:
    if db.query(Program).count() > 0:
        return
    for program_data in PROGRAMS:
        payload = dict(program_data)
        medications = payload.pop("medications")
        program = Program(**payload)
        db.add(program)
        db.flush()
        for med in medications:
            db.add(Medication(program_id=program.id, **med))
    db.commit()
