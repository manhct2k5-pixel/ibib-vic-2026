"""Test pipeline retrieve+expand và nối vào /api/chat (Story 1.3)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from kb.factory import get_repository
from pipeline.query import gather_candidates
from pipeline.retrieve import retrieve

CORPUS = Path(__file__).resolve().parents[2] / "data" / "sample" / "corpus.json"
TODAY = date(2026, 7, 17)


def test_gather_pulls_referenced_clause() -> None:
    repo = get_repository(str(CORPUS))
    ids = [c.clause_id for c in gather_candidates(repo, "vốn tự có", TODAY)]
    assert "TT41/Điều 10" in ids          # khớp trực tiếp
    assert "TT41/Điều 6.3" in ids          # được Điều 10 dẫn chiếu (FR-5)


def test_gather_no_duplicates() -> None:
    repo = get_repository(str(CORPUS))
    ids = [c.clause_id for c in gather_candidates(repo, "vốn tự có", TODAY)]
    assert len(ids) == len(set(ids))


def test_retrieve_excludes_expired() -> None:
    # Đảm bảo temporal của Story 1.3: search trực tiếp KHÔNG trả bản hết hạn.
    repo = get_repository(str(CORPUS))
    ids = [c.clause_id for c in retrieve(repo, "tỷ lệ an toàn vốn", TODAY)]
    assert "TT22/Điều 1" in ids          # bản 9% còn hiệu lực
    assert "TT41/Điều 6.3" not in ids     # bản 8% đã hết hiệu lực


def test_chat_returns_real_sources() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        resp = client.post(
            "/api/chat", json={"question": "Tỷ lệ an toàn vốn tối thiểu?"}
        )
        assert resp.status_code == 200
        data = resp.json()
        src_ids = [s["clause_id"] for s in data["sources"]]
        assert src_ids  # có nguồn thật
        assert "TT22/Điều 1" in src_ids  # bản còn hiệu lực (9%) có mặt


def test_chat_empty_when_no_match() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        resp = client.post("/api/chat", json={"question": "zzz qqq khongkhopgi"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["sources"] == []
        assert "Không tìm thấy" in data["answer"]


def test_chat_bad_asof_returns_400() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        resp = client.post(
            "/api/chat", json={"question": "CAR", "asOf": "17-07-2026"}
        )
        assert resp.status_code == 400
        assert "detail" in resp.json()
