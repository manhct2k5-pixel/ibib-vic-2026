"""Test tối thiểu Story 1.1: fail-fast khi thiếu corpus + đúng hình dạng contract."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from kb.repository import CorpusNotFoundError

CORPUS = Path(__file__).resolve().parents[2] / "data" / "sample" / "corpus.json"


def test_chat_returns_contract_shape() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        resp = client.post("/api/chat", json={"question": "Tỷ lệ an toàn vốn tối thiểu?"})
        assert resp.status_code == 200
        data = resp.json()
        # answer là chuỗi (AD-6)
        assert isinstance(data["answer"], str) and data["answer"]
        # có ít nhất 1 nguồn, kèm clause_id (AD-6, FR-13)
        assert len(data["sources"]) >= 1
        assert data["sources"][0]["clause_id"]
        assert "conflictWarning" in data


def test_chat_accepts_asof_and_mode() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        resp = client.post(
            "/api/chat",
            json={"question": "CAR?", "asOf": "2022-06-01", "mode": "baseline"},
        )
        assert resp.status_code == 200


def test_missing_corpus_fails_fast() -> None:
    app = create_app("/tmp/khong-ton-tai-corpus-12345.json")
    with pytest.raises(CorpusNotFoundError):
        with TestClient(app):
            pass
