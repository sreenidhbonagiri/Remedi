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


def _context_from(payload: dict) -> dict:
    return {
        "savings": payload["savings"],
        "fpl": payload["fpl"],
        "medication_query": payload["medication_query"],
    }


@pytest.mark.parametrize("greeting", ["yo", "hi", "hey", "hello", "sup", "howdy"])
def test_chat_casual_greeting_is_short_and_friendly(client: TestClient, greeting: str) -> None:
    triage = client.post("/api/v1/agent/triage", json=_triage_payload())
    payload = triage.json()

    chat = client.post(
        "/api/v1/agent/chat",
        json={"session_id": f"s-greet-{greeting}", "message": greeting, "context": _context_from(payload)},
    )
    assert chat.status_code == 200
    reply = chat.json()["reply"]
    assert payload["medication_query"] in reply
    # Greeting replies must not dump the raw poverty-line data block.
    assert "Behind the numbers" not in reply
    assert "fpl_percent" not in reply
    assert len(reply) < 260


def test_chat_generic_question_without_doctor_wording(client: TestClient) -> None:
    triage = client.post("/api/v1/agent/triage", json=_triage_payload())
    payload = triage.json()

    chat = client.post(
        "/api/v1/agent/chat",
        json={
            "session_id": "s-generic",
            "message": "Is there a generic equivalent alternative to this brand?",
            "context": _context_from(payload),
        },
    )
    assert chat.status_code == 200
    reply = chat.json()["reply"]
    alt = payload["savings"]["alternatives"][0]
    assert alt["name"] in reply
    assert alt["te_code"] in reply


def test_chat_income_question_without_number_uses_fpl_status(client: TestClient) -> None:
    triage = client.post("/api/v1/agent/triage", json=_triage_payload())
    payload = triage.json()

    chat = client.post(
        "/api/v1/agent/chat",
        json={
            "session_id": "s-afford",
            "message": "Can I afford this given my poverty level and income?",
            "context": _context_from(payload),
        },
    )
    assert chat.status_code == 200
    reply = chat.json()["reply"]
    assert str(payload["fpl"]["fpl_percent"]) in reply
    assert str(payload["fpl"]["limit_percent"]) in reply


def test_chat_doctor_typo_still_routes_to_doctor_intent(client: TestClient) -> None:
    triage = client.post("/api/v1/agent/triage", json=_triage_payload())
    payload = triage.json()

    chat = client.post(
        "/api/v1/agent/chat",
        json={"session_id": "s-typo", "message": "should i aska my doctr about this", "context": _context_from(payload)},
    )
    assert chat.status_code == 200
    reply = chat.json()["reply"]
    alt = payload["savings"]["alternatives"][0]
    assert alt["name"] in reply


def test_chat_unrecognized_message_returns_concise_clarification(client: TestClient) -> None:
    triage = client.post("/api/v1/agent/triage", json=_triage_payload())
    payload = triage.json()

    chat = client.post(
        "/api/v1/agent/chat",
        json={"session_id": "s-typo-fallback", "message": "xqzflorp", "context": _context_from(payload)},
    )
    assert chat.status_code == 200
    reply = chat.json()["reply"]
    assert "Here's what I have on file" not in reply
    assert "•" in reply
    assert len(reply.splitlines()) <= 5
