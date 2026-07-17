"""Test as-of time-travel, thay thế một phần, và đánh dấu đã thay thế (Story 1.4)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from kb.factory import get_repository
from pipeline.annotate import annotate
from pipeline.query import gather_candidates

CORPUS = Path(__file__).resolve().parents[2] / "data" / "sample" / "corpus.json"
TODAY = date(2026, 7, 17)
PAST = date(2019, 6, 1)


def _client():
    return TestClient(create_app(str(CORPUS)))


def test_asof_past_returns_old_version() -> None:
    with _client() as client:
        resp = client.post(
            "/api/chat",
            json={"question": "tỷ lệ an toàn vốn", "asOf": "2019-06-01"},
        )
        ids = [s["clause_id"] for s in resp.json()["sources"]]
        assert "TT41/Điều 6.3" in ids       # 8% còn hiệu lực năm 2019
        assert "TT22/Điều 1" not in ids      # 9% chưa hiệu lực (eff 2023)


def test_asof_today_returns_new_version() -> None:
    with _client() as client:
        resp = client.post("/api/chat", json={"question": "tỷ lệ an toàn vốn"})
        ids = [s["clause_id"] for s in resp.json()["sources"]]
        assert "TT22/Điều 1" in ids


def test_expired_reference_marked_superseded() -> None:
    with _client() as client:
        resp = client.post("/api/chat", json={"question": "tỷ lệ an toàn vốn"})
        sources = resp.json()["sources"]
        old = next((s for s in sources if s["clause_id"] == "TT41/Điều 6.3"), None)
        assert old is not None            # bị kéo vào qua dẫn chiếu (Điều 10)
        assert old["is_current"] is False
        assert old["superseded_by"] == "TT22/Điều 1"


def test_partial_supersession() -> None:
    repo = get_repository(str(CORPUS))
    clauses = gather_candidates(repo, "báo cáo định kỳ", TODAY)
    views = {v.clause.clause_id: v for v in annotate(repo, clauses, TODAY)}
    assert "TT41/Điều 8.1" in views and views["TT41/Điều 8.1"].is_current
    # 8.2 bị bãi bỏ: không phải một nguồn còn hiệu lực
    assert "TT41/Điều 8.2" not in views or not views["TT41/Điều 8.2"].is_current


def test_annotate_marks_current() -> None:
    repo = get_repository(str(CORPUS))
    clauses = gather_candidates(repo, "tỷ lệ an toàn vốn", TODAY)
    views = {v.clause.clause_id: v for v in annotate(repo, clauses, TODAY)}
    assert views["TT22/Điều 1"].is_current is True
    assert views["TT22/Điều 1"].superseded_by is None
