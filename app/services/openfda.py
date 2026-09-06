"""Async openFDA NDC client with safe medication upserts."""

from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.seed import CATALOG_PROGRAM_NAME, _ensure_catalog_program
from app.models.medication import Medication

OPENFDA_NDC_URL = "https://api.fda.gov/drug/ndc.json"
DEFAULT_LIMIT = 30


class OpenFDAError(Exception):
    """Raised when the openFDA HTTP API cannot be reached or returns an error payload."""


def parse_ndc_result(item: dict[str, Any]) -> dict[str, str]:
    brand = str(item.get("brand_name") or item.get("generic_name") or "").strip()
    ingredients = item.get("active_ingredients") or item.get("active_ingredient") or []
    if isinstance(ingredients, dict):
        ingredients = [ingredients]
    if not isinstance(ingredients, list):
        ingredients = []

    active = ""
    strength = ""
    if ingredients:
        first = ingredients[0] if isinstance(ingredients[0], dict) else {"name": str(ingredients[0])}
        active = str(first.get("name") or "").strip()
        strength = str(first.get("strength") or "").strip()
    if not strength:
        strength = str(item.get("strength") or "").strip()
    if not active:
        active = str(item.get("generic_name") or "").strip()

    form = str(item.get("dosage_form") or "").strip()
    ndc = str(item.get("product_ndc") or "").strip()
    if not ndc:
        packaging = item.get("packaging") or []
        if packaging and isinstance(packaging[0], dict):
            ndc = str(packaging[0].get("package_ndc") or "").strip()

    return {
        "name": brand,
        "generic_name": active,
        "form": form,
        "strength": strength,
        "ndc": ndc,
    }


async def fetch_ndc_directory(
    search: str | None = None,
    limit: int = DEFAULT_LIMIT,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    params: dict[str, str | int] = {"limit": limit}
    if search:
        params["search"] = search

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=20.0)
    try:
        response = await client.get(OPENFDA_NDC_URL, params=params)
        if response.status_code == 404:
            return {"results": [], "meta": {"results": {"total": 0}}}
        if response.status_code >= 400:
            raise OpenFDAError(f"openFDA returned HTTP {response.status_code}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise OpenFDAError("openFDA returned a non-object JSON payload")
        payload.setdefault("results", [])
        return payload
    except httpx.HTTPError as exc:
        raise OpenFDAError(f"openFDA request failed: {exc}") from exc
    finally:
        if owns_client and client is not None:
            await client.aclose()


def upsert_medication_from_ndc(db: Session, parsed: dict[str, str], program_id: int) -> Medication:
    name = parsed.get("name") or ""
    strength = parsed.get("strength") or ""
    ndc = parsed.get("ndc") or ""
    existing: Medication | None = None
    if ndc:
        existing = db.query(Medication).filter(Medication.ndc == ndc).one_or_none()
    if existing is None and name:
        by_name = db.query(Medication).filter(func.lower(Medication.name) == name.lower())
        if strength:
            existing = (
                by_name.filter(func.lower(Medication.strength) == strength.lower())
                .order_by(Medication.id.asc())
                .first()
            )
        if existing is None:
            existing = by_name.order_by(Medication.id.asc()).first()

    if existing is None:
        existing = Medication(
            name=name or "Unknown",
            generic_name=parsed.get("generic_name") or "",
            form=parsed.get("form") or "",
            strength=strength,
            ndc=ndc,
            program_id=program_id,
        )
        db.add(existing)
        db.flush()
        return existing

    if parsed.get("generic_name") and not existing.generic_name:
        existing.generic_name = parsed["generic_name"]
    if parsed.get("form") and not existing.form:
        existing.form = parsed["form"]
    if strength and not existing.strength:
        existing.strength = strength
    if ndc and not existing.ndc:
        existing.ndc = ndc
    return existing


async def sync_ndc_to_medications(
    db: Session,
    search: str | None = None,
    limit: int = DEFAULT_LIMIT,
    client: httpx.AsyncClient | None = None,
) -> list[Medication]:
    try:
        payload = await fetch_ndc_directory(search=search, limit=limit, client=client)
    except OpenFDAError:
        return []

    catalog = _ensure_catalog_program(db)
    upserted: list[Medication] = []
    for item in payload.get("results") or []:
        if not isinstance(item, dict):
            continue
        parsed = parse_ndc_result(item)
        if not parsed.get("name"):
            continue
        upserted.append(upsert_medication_from_ndc(db, parsed, catalog.id))
    db.commit()
    return upserted


def catalog_program_name() -> str:
    return CATALOG_PROGRAM_NAME
