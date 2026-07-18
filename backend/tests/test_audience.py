"""Test chế độ khách hàng (audience/scope) — Story 1.7. Không rò dữ liệu nội bộ."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from kb.factory import get_repository

CORPUS = Path(__file__).resolve().parents[2] / "data" / "sample" / "corpus.json"
TODAY = date(2026, 7, 17)


def test_search_public_scope_excludes_internal() -> None:
    repo = get_repository(str(CORPUS))
    ids = [c.clause_id for c in repo.search("tỷ lệ an toàn vốn", TODAY, scope="public")]
    assert "QD-INT/Điều 2" not in ids
    assert "TT22/Điều 1" in ids


def test_expand_public_scope_skips_internal() -> None:
    repo = get_repository(str(CORPUS))
    # QD-INT/Điều 2 không có cạnh REFERENCES tới, nên kiểm gián tiếp: scope public
    # không trả clause internal nào.
    out = repo.expand_references(["TT41/Điều 10"], scope="public")
    assert all(c.visibility == "public" for c in out)


def test_chat_customer_only_public_sources() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        resp = client.post(
            "/api/chat",
            json={"question": "tỷ lệ an toàn vốn", "audience": "customer"},
        )
        assert resp.status_code == 200
        ids = [s["clause_id"] for s in resp.json()["sources"]]
        assert "QD-INT/Điều 2" not in ids
        assert ids  # vẫn có nguồn công khai


def test_chat_employee_sees_internal() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        resp = client.post(
            "/api/chat",
            json={"question": "tỷ lệ an toàn vốn", "audience": "employee"},
        )
        ids = [s["clause_id"] for s in resp.json()["sources"]]
        assert "QD-INT/Điều 2" in ids  # nhân viên thấy nội bộ
