"""LangGraph Affordable Medication Sourcing Copilot.

Workflow: extract_and_triage -> execute_tools -> synthesize_action_plan.

Numbers and eligibility caps in the action plan are copied from tool JSON only.
When no LLM API key is configured, extraction and synthesis use deterministic
string templates so tests and offline runs stay reliable.
"""

from __future__ import annotations

import json
import os
import re
from typing import Annotated, Any, TypedDict

import operator
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.medication import Medication
from app.services.agent_tools import build_agent_tools

GRAPH_NODES = ("extract_and_triage", "execute_tools", "synthesize_action_plan")

STATE_NAMES = {
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "DISTRICT OF COLUMBIA": "DC",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
}


class AgentState(TypedDict, total=False):
    query: str
    annual_income: float | None
    household_size: int | None
    state: str
    is_uninsured: bool
    is_medicare: bool
    medication_query: str
    extracted: dict[str, Any]
    tool_results: dict[str, str]
    action_plan: str
    visited_nodes: Annotated[list[str], operator.add]


def llm_api_key() -> str:
    return (os.environ.get("OPENAI_API_KEY") or getattr(settings, "openai_api_key", "") or "").strip()


def _loads(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _catalog_terms(db: Session) -> list[str]:
    rows = db.query(Medication.name, Medication.generic_name).all()
    terms = {name.strip() for name, _generic in rows if name and name.strip()}
    terms.update(generic.strip() for _name, generic in rows if generic and generic.strip())
    return sorted(terms, key=len, reverse=True)


def _heuristic_extract(query: str, db: Session) -> dict[str, Any]:
    text = query or ""
    upper = text.upper()
    extracted: dict[str, Any] = {}

    for term in _catalog_terms(db):
        if re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE):
            extracted["medication_query"] = term
            break

    income_match = re.search(
        r"(?:earn(?:s|ed|ing)?|income|make[s]?|salary)[^\d$]{0,12}\$?\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?",
        text,
        flags=re.IGNORECASE,
    )
    if not income_match:
        income_match = re.search(r"\$\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", text)
    if income_match:
        extracted["annual_income"] = float(income_match.group(1).replace(",", ""))

    household_match = re.search(
        r"(?:household(?:\s+size)?|family|family of|household of)\s*(?:is\s*|of\s*|:\s*)?(\d{1,2})",
        text,
        flags=re.IGNORECASE,
    )
    if household_match:
        extracted["household_size"] = int(household_match.group(1))

    for name, code in STATE_NAMES.items():
        if re.search(rf"\b{name}\b", upper):
            extracted["state"] = code
            break
    else:
        state_code = re.search(r"\b([A-Z]{2})\b", text)
        if state_code and state_code.group(1) in set(STATE_NAMES.values()):
            extracted["state"] = state_code.group(1)

    if re.search(r"\buninsured\b", text, flags=re.IGNORECASE):
        extracted["is_uninsured"] = True
    elif re.search(r"\binsured\b", text, flags=re.IGNORECASE):
        extracted["is_uninsured"] = False

    if re.search(r"\bmedicare\b", text, flags=re.IGNORECASE):
        extracted["is_medicare"] = True

    return extracted


def _llm_extract(query: str) -> dict[str, Any] | None:
    if not llm_api_key():
        return None
    try:
        from langchain_openai import ChatOpenAI
        from pydantic import BaseModel, Field

        class Extraction(BaseModel):
            medication_query: str = ""
            annual_income: float | None = None
            household_size: int | None = None
            state: str | None = None
            is_uninsured: bool | None = None
            is_medicare: bool | None = None

        llm = ChatOpenAI(
            model=getattr(settings, "openai_model", "gpt-4o-mini"),
            api_key=llm_api_key(),
            temperature=0,
        )
        structured = llm.with_structured_output(Extraction)
        result = structured.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        "Extract medication sourcing facts from the patient message. "
                        "Do not invent income, household size, FPL percentages, or prices."
                    ),
                },
                {"role": "user", "content": query},
            ]
        )
        return result.model_dump()
    except Exception:
        return None


def _money(value: float | int | None) -> str:
    if value is None:
        return "not provided in tool output"
    return f"${float(value):,.2f}"


def _synthesize_from_tools(state: AgentState) -> str:
    tools = state.get("tool_results") or {}
    fpl = _loads(tools.get("evaluate_federal_poverty_level"))
    savings = _loads(tools.get("find_medication_savings"))
    medication = state.get("medication_query") or savings.get("matched_medication") or "not identified"

    lines = [
        "AFFORDABLE MEDICATION SOURCING PLAN",
        "All dollar amounts, FPL percentages, and eligibility caps below are copied from tool JSON.",
        "",
        f"Medication: {medication}",
    ]

    if fpl:
        lines.extend(
            [
                (
                    f"2026 FPL: household of {fpl['household_size']} in {fpl['state']} "
                    f"has a 100% guideline of {_money(fpl['guideline'])}."
                ),
                (
                    f"Reported income {_money(fpl['annual_income'])} is {fpl['fpl_percent']}% FPL "
                    f"(tool field fpl_percent)."
                ),
                (
                    f"Standard 400% cap from the FPL tool is {_money(fpl['limit_amount'])} "
                    f"(limit_percent={fpl['limit_percent']}; meets_threshold={fpl['meets_threshold']})."
                ),
            ]
        )
    else:
        lines.append("2026 FPL: income and household size were not available, so the FPL tool was not run.")

    lines.extend(["", "AB-rated generic alternatives (from find_medication_savings):"])
    alternatives = savings.get("alternatives") or []
    if not alternatives:
        notes = savings.get("notes") or ["No AB-rated alternatives were returned by the savings tool."]
        lines.append(f"- {notes[0]}")
    else:
        brand_price = savings.get("brand_cash_price")
        for alt in alternatives:
            lines.append(
                (
                    f"- {alt.get('name')} (TE {alt.get('te_code')}): cash {_money(alt.get('cash_price'))} "
                    f"versus brand {_money(alt.get('brand_cash_price', brand_price))}; "
                    f"save {_money(alt.get('savings_amount'))} ({alt.get('savings_percent')}%)."
                )
            )

    lines.extend(["", "Patient assistance programs (from find_medication_savings):"])
    programs = savings.get("eligible_programs") or []
    if not programs:
        lines.append("- No PAP matches were returned by the savings tool.")
    else:
        for program in programs:
            flag = program.get("eligible")
            if flag is True:
                status = "ELIGIBLE"
            elif flag is False:
                status = "NOT ELIGIBLE"
            else:
                status = "UNSCORED"
            lines.append(
                (
                    f"- {program.get('name')} ({program.get('manufacturer')}): {status} "
                    f"at cap {program.get('fpl_limit_percent')}% FPL. "
                    f"{program.get('reason')} Phone: {program.get('phone')}."
                )
            )

    lines.extend(
        [
            "",
            "Next steps",
            "1. Confirm the AB-rated alternative with the prescriber before switching.",
            "2. If a PAP is ELIGIBLE, generate the application PDF from this copilot.",
            "3. Do not rely on numbers that are not present in the tool JSON above.",
        ]
    )
    return "\n".join(lines)


def _llm_synthesize(state: AgentState) -> str | None:
    if not llm_api_key():
        return None
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=getattr(settings, "openai_model", "gpt-4o-mini"),
            api_key=llm_api_key(),
            temperature=0,
        )
        tool_json = json.dumps(state.get("tool_results") or {}, indent=2)
        message = llm.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        "You are an Affordable Medication Sourcing Copilot. "
                        "STRICT GUARDRAIL: every number you cite (cash prices, savings "
                        "percentages, FPL percentages, eligibility caps, phone numbers) MUST "
                        "appear verbatim in the tool JSON. Never invent, recompute, or round "
                        "figures. If a value is missing, say it was not returned by the tool."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Patient query: {state.get('query')}\n\n"
                        f"Tool JSON:\n{tool_json}\n\n"
                        "Write a concise action plan that cites only those tool values."
                    ),
                },
            ]
        )
        content = getattr(message, "content", "")
        return str(content) if content else None
    except Exception:
        return None


def build_copilot_graph(db: Session):
    tools = build_agent_tools(db)
    tools_by_name: dict[str, BaseTool] = {tool.name: tool for tool in tools}

    def extract_and_triage(state: AgentState) -> dict[str, Any]:
        query = state.get("query") or ""
        extracted = _llm_extract(query) or _heuristic_extract(query, db)
        medication = (
            state.get("medication_query")
            or extracted.get("medication_query")
            or ""
        )
        income = state.get("annual_income")
        if income is None:
            income = extracted.get("annual_income")
        household = state.get("household_size")
        if household is None:
            household = extracted.get("household_size")
        state_code = state.get("state") or extracted.get("state") or "PA"
        uninsured = state.get("is_uninsured")
        if uninsured is None:
            uninsured = extracted.get("is_uninsured", True)
        medicare = state.get("is_medicare")
        if medicare is None:
            medicare = extracted.get("is_medicare", False)
        return {
            "visited_nodes": ["extract_and_triage"],
            "extracted": extracted,
            "medication_query": medication,
            "annual_income": income,
            "household_size": household,
            "state": state_code,
            "is_uninsured": bool(uninsured),
            "is_medicare": bool(medicare),
        }

    def execute_tools(state: AgentState) -> dict[str, Any]:
        results: dict[str, str] = {}
        income = state.get("annual_income")
        household = state.get("household_size")
        state_code = state.get("state") or "PA"
        if income is not None and household:
            results["evaluate_federal_poverty_level"] = tools_by_name[
                "evaluate_federal_poverty_level"
            ].invoke(
                {
                    "annual_income": income,
                    "household_size": household,
                    "state": state_code,
                    "limit_percent": 400.0,
                }
            )
        medication = (state.get("medication_query") or "").strip()
        if medication:
            payload: dict[str, Any] = {
                "query_name": medication,
                "state": state_code,
                "is_uninsured": bool(state.get("is_uninsured", True)),
                "is_medicare": bool(state.get("is_medicare", False)),
            }
            if income is not None:
                payload["annual_income"] = income
            if household is not None:
                payload["household_size"] = household
            results["find_medication_savings"] = tools_by_name["find_medication_savings"].invoke(payload)
        return {"visited_nodes": ["execute_tools"], "tool_results": results}

    def synthesize_action_plan(state: AgentState) -> dict[str, Any]:
        plan = _llm_synthesize(state) or _synthesize_from_tools(state)
        return {"visited_nodes": ["synthesize_action_plan"], "action_plan": plan}

    graph = StateGraph(AgentState)
    graph.add_node("extract_and_triage", extract_and_triage)
    graph.add_node("execute_tools", execute_tools)
    graph.add_node("synthesize_action_plan", synthesize_action_plan)
    graph.add_edge(START, "extract_and_triage")
    graph.add_edge("extract_and_triage", "execute_tools")
    graph.add_edge("execute_tools", "synthesize_action_plan")
    graph.add_edge("synthesize_action_plan", END)
    return graph.compile()


def run_copilot_agent(
    db: Session,
    query: str,
    annual_income: float | None = None,
    household_size: int | None = None,
    state: str = "PA",
    is_uninsured: bool = True,
    is_medicare: bool = False,
) -> AgentState:
    graph = build_copilot_graph(db)
    return graph.invoke(
        {
            "query": query,
            "annual_income": annual_income,
            "household_size": household_size,
            "state": state,
            "is_uninsured": is_uninsured,
            "is_medicare": is_medicare,
            "visited_nodes": [],
        }
    )
