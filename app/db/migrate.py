"""Additive SQLite column upgrades so existing local databases keep working."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def apply_sqlite_additions(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        if "medications" in tables:
            cols = {column["name"] for column in inspector.get_columns("medications")}
            additions = {
                "ndc": "VARCHAR(32) DEFAULT ''",
                "cash_price": "FLOAT",
                "te_code": "VARCHAR(8) DEFAULT ''",
                "is_generic": "BOOLEAN DEFAULT 0",
            }
            for name, ddl in additions.items():
                if name not in cols:
                    conn.execute(text(f"ALTER TABLE medications ADD COLUMN {name} {ddl}"))
        if "programs" in tables:
            cols = {column["name"] for column in inspector.get_columns("programs")}
            if "is_pap" not in cols:
                conn.execute(text("ALTER TABLE programs ADD COLUMN is_pap BOOLEAN DEFAULT 1"))
