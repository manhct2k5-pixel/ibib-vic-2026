"""Test Story 3.1: rule phát hiện xung đột + scope + wiring conflictWarning.

- find_conflicts(scope="public") bỏ clause internal (AD-11).
- check_conflicts: chỉ cảnh báo cặp xung đột có topic thuộc candidate; None nếu không.
- /api/chat: employee thấy cảnh báo an toàn vốn (9% vs 8%); customer không (không rò internal).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from kb.factory import get_repository
from kb.models import Clause
from pipeline.conflict_check import check_conflicts

CORPUS = Path(__file__).resolve().parents[2] / "data" / "sample" / "corpus.json"
TODAY = date(2026, 7, 17)


def _repo():
    return get_repository(str(CORPUS))


def test_find_conflicts_scope_public_excludes_internal() -> None:
    repo = _repo()
    all_pairs = repo.find_conflicts(TODAY, scope="all")
    all_ids = {
        frozenset((p.clause_a.clause_id, p.clause_b.clause_id)) for p in all_pairs
    }
    assert frozenset(("TT22/Điều 1", "QD-INT/Điều 2")) in all_ids

    public_pairs = repo.find_conflicts(TODAY, scope="public")
    for p in public_pairs:
        assert "QD-INT/Điều 2" not in (p.clause_a.clause_id, p.clause_b.clause_id)


def test_check_conflicts_returns_warning_for_relevant_topic() -> None:
    repo = _repo()
    candidates = repo.search("tỷ lệ an toàn vốn", TODAY)  # topic ty_le_an_toan_von
    warning = check_conflicts(repo, candidates, TODAY, scope="all")
    assert warning is not None
    assert "TT22/Điều 1" in warning and "QD-INT/Điều 2" in warning


def test_check_conflicts_none_for_unrelated_topic() -> None:
    repo = _repo()
    # Candidate chỉ thuộc 'bao_cao_dinh_ky' — chủ đề không có xung đột giá trị số
    candidates = [
        Clause("X", "D", "Điều 1", "", date(2020, 1, 1), None, "bao_cao_dinh_ky", "public")
    ]
    warning = check_conflicts(repo, candidates, TODAY, scope="all")
    assert warning is None


def test_check_conflicts_public_scope_hides_internal() -> None:
    repo = _repo()
    candidates = repo.search("tỷ lệ an toàn vốn", TODAY, scope="public")
    warning = check_conflicts(repo, candidates, TODAY, scope="public")
    assert warning is None  # QD-INT (internal) bị loại → không còn cặp xung đột


def test_chat_employee_shows_conflict_warning() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        resp = client.post(
            "/api/chat",
            json={"question": "Tỷ lệ an toàn vốn tối thiểu?", "asOf": "2026-07-17"},
        )
        assert resp.status_code == 200
        warning = resp.json()["conflictWarning"]
        assert warning is not None
        assert "TT22/Điều 1" in warning and "QD-INT/Điều 2" in warning


def test_chat_customer_hides_conflict_warning() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        resp = client.post(
            "/api/chat",
            json={
                "question": "Tỷ lệ an toàn vốn tối thiểu?",
                "asOf": "2026-07-17",
                "audience": "customer",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["conflictWarning"] is None
