"""Test synthesize + provider LLM (dùng MockLLM, KHÔNG gọi mạng) — Story 1.5."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from kb.factory import get_repository
from pipeline.annotate import annotate
from pipeline.query import gather_candidates
from pipeline.synthesize import synthesize
from providers.llm import MockLLM, get_llm

CORPUS = Path(__file__).resolve().parents[2] / "data" / "sample" / "corpus.json"
TODAY = date(2026, 7, 17)


@pytest.fixture(autouse=True)
def _no_llm_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)


def _views(question: str):
    repo = get_repository(str(CORPUS))
    return annotate(repo, gather_candidates(repo, question, TODAY), TODAY)


def test_get_llm_returns_mock_without_key() -> None:
    assert isinstance(get_llm(), MockLLM)


def test_synthesize_mentions_clause_ids() -> None:
    views = _views("tỷ lệ an toàn vốn")
    answer = synthesize(MockLLM(), "Tỷ lệ an toàn vốn?", views)
    assert answer
    assert "TT22/Điều 1" in answer


def test_synthesize_notes_superseded() -> None:
    views = _views("tỷ lệ an toàn vốn")  # có Điều 6.3 (đã thay thế) qua dẫn chiếu
    answer = synthesize(MockLLM(), "CAR?", views)
    assert "THAY THẾ" in answer.upper()


def test_chat_uses_llm_answer() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        resp = client.post("/api/chat", json={"question": "Tỷ lệ an toàn vốn?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"]
        assert [s["clause_id"] for s in data["sources"]]
