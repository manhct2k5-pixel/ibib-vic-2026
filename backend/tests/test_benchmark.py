"""Test Epic 4: chế độ baseline (RAG thường) vs system.

- search(apply_temporal=False) → thấy cả bản hết hiệu lực (baseline không lọc temporal).
- /api/chat mode=baseline → nguồn dính TT41/Điều 6.3 (8%, cũ); mode=system → không.
- baseline không kéo dẫn chiếu (expand tắt); baseline không có conflictWarning.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from kb.factory import get_repository

CORPUS = Path(__file__).resolve().parents[2] / "data" / "sample" / "corpus.json"
TODAY = date(2026, 7, 17)


def _repo():
    return get_repository(str(CORPUS))


def _ids(resp):
    return {s["clause_id"] for s in resp.json()["sources"]}


def _source(resp, cid):
    for s in resp.json()["sources"]:
        if s["clause_id"] == cid:
            return s
    return None


def test_search_no_temporal_includes_expired() -> None:
    repo = _repo()
    active = {c.clause_id for c in repo.search("tỷ lệ an toàn vốn", TODAY)}
    naive = {
        c.clause_id
        for c in repo.search("tỷ lệ an toàn vốn", TODAY, apply_temporal=False)
    }
    assert "TT41/Điều 6.3" not in active  # bản 8% hết hiệu lực bị lọc (system)
    assert "TT41/Điều 6.3" in naive  # baseline thấy bản cũ


def test_search_no_temporal_still_filters_scope() -> None:
    repo = _repo()
    naive_public = repo.search(
        "tỷ lệ an toàn vốn", TODAY, scope="public", apply_temporal=False
    )
    assert all(c.visibility == "public" for c in naive_public)


def test_chat_baseline_shows_expired_source() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        base = client.post(
            "/api/chat",
            json={
                "question": "Tỷ lệ an toàn vốn tối thiểu?",
                "asOf": "2026-07-17",
                "mode": "baseline",
            },
        )
        sysm = client.post(
            "/api/chat",
            json={
                "question": "Tỷ lệ an toàn vốn tối thiểu?",
                "asOf": "2026-07-17",
                "mode": "system",
            },
        )
        assert base.status_code == 200 and sysm.status_code == 200
        # Baseline coi bản cũ 8% như còn hiệu lực (ngây thơ, không temporal)
        b63 = _source(base, "TT41/Điều 6.3")
        assert b63 is not None and b63["is_current"] is True
        # System: bản cũ vắng mặt HOẶC bị đánh dấu đã thay thế (temporal-aware)
        s63 = _source(sysm, "TT41/Điều 6.3")
        assert s63 is None or s63["is_current"] is False


def test_chat_baseline_no_conflict_warning() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        base = client.post(
            "/api/chat",
            json={
                "question": "Tỷ lệ an toàn vốn tối thiểu?",
                "asOf": "2026-07-17",
                "mode": "baseline",
            },
        )
        assert base.json()["conflictWarning"] is None


def test_chat_baseline_includes_expired_not_referenced() -> None:
    # Bằng chứng temporal: TT41/Điều 8.2 (hết hiệu lực 2023, KHÔNG được dẫn chiếu)
    # → baseline (không lọc hiệu lực) thấy; system (lọc hiệu lực, không có edge kéo
    # lại) KHÔNG thấy. Khác với 6.3 (được REFERENCES nên system vẫn kéo vào).
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        payload = {"question": "Điều 10 vốn tự có", "asOf": "2026-07-17"}
        base = client.post("/api/chat", json={**payload, "mode": "baseline"})
        sysm = client.post("/api/chat", json={**payload, "mode": "system"})
        assert base.status_code == 200 and sysm.status_code == 200
        assert "TT41/Điều 8.2" in _ids(base)  # baseline dính bản hết hiệu lực
        assert "TT41/Điều 8.2" not in _ids(sysm)  # system loại (temporal + không dẫn chiếu)
