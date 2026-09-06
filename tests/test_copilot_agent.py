from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.agent_tools import build_agent_tools
from app.services.copilot_agent import GRAPH_NODES, build_copilot_graph, run_copilot_agent


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("app.services.copilot_agent.llm_api_key", lambda: "")


def test_savings_and_fpl_tools_return_json(db_session: Session) -> None:
    tools = {tool.name: tool for tool in build_agent_tools(db_session)}
    assert set(tools) == {"find_medication_savings", "evaluate_federal_poverty_level"}

    fpl_raw = tools["evaluate_federal_poverty_level"].invoke(
        {"annual_income": 35000, "household_size": 1, "state": "PA", "limit_percent": 400.0}
    )
    fpl = json.loads(fpl_raw)
    assert fpl["fpl_year"] == 2026
    assert fpl["guideline"] == 15960
    assert fpl["fpl_percent"] == 219.3
    assert fpl["limit_percent"] == 400.0
    assert fpl["meets_threshold"] is True

    savings_raw = tools["find_medication_savings"].invoke(
        {
            "query_name": "Humira",
            "annual_income": 35000,
            "household_size": 1,
            "state": "PA",
            "is_uninsured": True,
            "is_medicare": False,
        }
    )
    savings = json.loads(savings_raw)
    assert savings["matched_medication"] == "Humira"
    assert savings["fpl_percent"] == 219.3
    assert savings["alternatives"][0]["te_code"] == "AB"
    assert savings["alternatives"][0]["savings_percent"] == 80.0


def test_graph_transitions_and_guardrail_numbers(db_session: Session) -> None:
    graph = build_copilot_graph(db_session)
    node_ids = set(graph.get_graph().nodes)
    assert set(GRAPH_NODES).issubset(node_ids)

    result = run_copilot_agent(
        db_session,
        query="I take Humira and earn $35,000. Household of 1 in PA, uninsured.",
        annual_income=35000,
        household_size=1,
        state="PA",
        is_uninsured=True,
        is_medicare=False,
    )
    assert result["visited_nodes"] == list(GRAPH_NODES)
    assert result["medication_query"]
    tools = result["tool_results"]
    assert "evaluate_federal_poverty_level" in tools
    assert "find_medication_savings" in tools

    fpl = json.loads(tools["evaluate_federal_poverty_level"])
    savings = json.loads(tools["find_medication_savings"])
    plan = result["action_plan"]
    assert f"{fpl['fpl_percent']}% FPL" in plan
    assert f"limit_percent={fpl['limit_percent']}" in plan
    assert "ELIGIBLE" in plan
    alt = savings["alternatives"][0]
    assert f"({alt['savings_percent']}%)" in plan
    assert alt["te_code"] in plan
    abbvie = next(p for p in savings["eligible_programs"] if p["name"] == "myAbbVie Assist")
    assert str(abbvie["fpl_limit_percent"]) in plan
    assert "8000" in json.dumps(savings)
    assert "219.3" in json.dumps(fpl)
    # Guardrail: cited FPL percent, cap, and savings percent exist in tool JSON.
    for token in (str(fpl["fpl_percent"]), str(fpl["limit_percent"]), str(alt["savings_percent"])):
        assert token in json.dumps(tools)
        assert token in plan


def test_heuristic_extraction_without_explicit_fields(db_session: Session) -> None:
    result = run_copilot_agent(
        db_session,
        query="Need help affording Januvia. I earn 20000, household of 2 in Illinois, uninsured.",
    )
    assert result["medication_query"].lower() in {"januvia", "sitagliptin"}
    assert result["annual_income"] == 20000.0
    assert result["household_size"] == 2
    assert result["state"] == "IL"
    fpl = json.loads(result["tool_results"]["evaluate_federal_poverty_level"])
    assert fpl["fpl_percent"] == round((20000 / 21640) * 100, 1)
    assert str(fpl["fpl_percent"]) in result["action_plan"]


def test_triage_endpoint_returns_action_plan(client: TestClient) -> None:
    response = client.post(
        "/api/v1/agent/triage",
        json={
            "query": "I take Humira, earn 35000, household of 1 in PA, uninsured.",
            "annual_income": 35000,
            "household_size": 1,
            "state": "PA",
            "is_uninsured": True,
            "is_medicare": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["visited_nodes"] == list(GRAPH_NODES)
    assert "219.3" in payload["action_plan"]
    assert payload["fpl"]["fpl_percent"] == 219.3
    assert payload["savings"]["alternatives"][0]["savings_percent"] == 80.0
    assert payload["fpl"]["limit_percent"] == 400.0
    assert str(payload["fpl"]["limit_percent"]) in payload["action_plan"]


def test_landing_and_app_pages_render(client: TestClient) -> None:
    landing = client.get("/")
    assert landing.status_code == 200
    assert "Remedi" in landing.text
    assert "Launch App" in landing.text

    workspace = client.get("/app")
    assert workspace.status_code == 200
    assert "Remedi" in workspace.text
    assert "Remy" in workspace.text
    assert "Humira" in workspace.text
    assert "triage-form" in workspace.text
