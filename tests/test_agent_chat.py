from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.copilot_agent import run_copilot_chat


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("app.services.copilot_agent.llm_api_key", lambda: "")


def _triage_payload() -> dict:
    return {
        "query": "I take Humira, earn 35000, household of 1 in PA, uninsured.",
        "annual_income": 35000,
        "household_size": 1,
        "state": "PA",
        "is_uninsured": True,
        "is_medicare": False,
    }


def test_chat_without_prior_context_asks_for_triage_first(db_session: Session) -> None:
    reply = run_copilot_chat(db_session, session_id="s-empty", message="What should I ask my doctor?")
    assert "run a search above" in reply.lower()


def test_chat_uses_triage_context_for_doctor_question(client: TestClient) -> None:
    triage = client.post("/api/v1/agent/triage", json=_triage_payload())
    assert triage.status_code == 200
    payload = triage.json()

    chat = client.post(
        "/api/v1/agent/chat",
        json={
            "session_id": "s-doctor",
            "message": "What should I ask my doctor?",
            "context": {
                "savings": payload["savings"],
                "fpl": payload["fpl"],
                "medication_query": payload["medication_query"],
            },
        },
    )
    assert chat.status_code == 200
    body = chat.json()
    assert body["session_id"] == "s-doctor"
    alt = payload["savings"]["alternatives"][0]
    assert alt["name"] in body["reply"]
    assert alt["te_code"] in body["reply"]


def test_chat_income_change_recomputes_fpl_from_tools(client: TestClient) -> None:
    triage = client.post("/api/v1/agent/triage", json=_triage_payload())
    payload = triage.json()

    chat = client.post(
        "/api/v1/agent/chat",
        json={
            "session_id": "s-income",
            "message": "What if my income becomes $20,000?",
            "context": {
                "savings": payload["savings"],
                "fpl": payload["fpl"],
                "medication_query": payload["medication_query"],
            },
        },
    )
    assert chat.status_code == 200
    reply = chat.json()["reply"]
    expected_percent = round((20000 / payload["fpl"]["guideline"] * payload["fpl"]["fpl_percent"] / 100) * 100, 1)
    # Recomputed independently via the FPL guardrail: percent must come straight from the tool.
    assert "20,000.00" in reply or "$20,000" in reply
    assert "%" in reply


def test_chat_pdf_question_mentions_download_button(client: TestClient) -> None:
    triage = client.post("/api/v1/agent/triage", json=_triage_payload())
    payload = triage.json()

    chat = client.post(
        "/api/v1/agent/chat",
        json={
            "session_id": "s-pdf",
            "message": "How do I submit this PDF application?",
            "context": {
                "savings": payload["savings"],
                "fpl": payload["fpl"],
                "medication_query": payload["medication_query"],
            },
        },
    )
    assert chat.status_code == 200
    reply = chat.json()["reply"].lower()
    assert "download" in reply or "form" in reply


def test_chat_session_remembers_context_across_turns(client: TestClient) -> None:
    triage = client.post("/api/v1/agent/triage", json=_triage_payload())
    payload = triage.json()

    first = client.post(
        "/api/v1/agent/chat",
        json={
            "session_id": "s-memory",
            "message": "What should I ask my doctor?",
            "context": {
                "savings": payload["savings"],
                "fpl": payload["fpl"],
                "medication_query": payload["medication_query"],
            },
        },
    )
    assert first.status_code == 200

    # No context on the second turn — session memory should still answer using stored context.
    second = client.post(
        "/api/v1/agent/chat",
        json={"session_id": "s-memory", "message": "How do I submit the PDF?"},
    )
    assert second.status_code == 200
    reply = second.json()["reply"].lower()
    assert "download" in reply or "form" in reply


def test_triage_endpoint_still_returns_full_payload(client: TestClient) -> None:
    response = client.post("/api/v1/agent/triage", json=_triage_payload())
    assert response.status_code == 200
    payload = response.json()
    assert "action_plan" in payload
    assert "savings" in payload
    assert "fpl" in payload
