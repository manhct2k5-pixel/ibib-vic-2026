"""Test StubRepository — 6 hàm interface, bám dữ liệu corpus.json mẫu."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from kb.factory import get_repository
from kb.repository import is_active
from kb.models import Clause

CORPUS = Path(__file__).resolve().parents[2] / "data" / "sample" / "corpus.json"
TODAY = date(2026, 7, 17)


def _repo():
    return get_repository(str(CORPUS))


def test_is_active_null_expiry() -> None:
    c = Clause("X", "D", "Điều 1", "", date(2020, 1, 1), None, "t", "public")
    assert is_active(c, TODAY) is True
    c2 = Clause("Y", "D", "Điều 1", "", date(2016, 1, 1), date(2023, 1, 1), "t", "public")
    assert is_active(c2, TODAY) is False


def test_search_filters_expired() -> None:
    ids = [c.clause_id for c in _repo().search("tỷ lệ an toàn vốn", TODAY)]
    assert "TT22/Điều 1" in ids          # 9%, còn hiệu lực
    assert "TT41/Điều 6.3" not in ids    # 8%, đã hết hiệu lực


def test_search_public_excludes_internal() -> None:
    results = _repo().search("tỷ lệ an toàn vốn", TODAY, scope="public")
    ids = [c.clause_id for c in results]
    assert "QD-INT/Điều 2" not in ids
    assert all(c.visibility == "public" for c in results)


def test_find_conflicts_detects_pair() -> None:
    pairs = _repo().find_conflicts(TODAY)
    got = {frozenset((p.clause_a.clause_id, p.clause_b.clause_id)) for p in pairs}
    assert frozenset(("TT22/Điều 1", "QD-INT/Điều 2")) in got


def test_expand_references() -> None:
    ids = [c.clause_id for c in _repo().expand_references(["TT41/Điều 10"])]
    assert "TT41/Điều 6.3" in ids


def test_version_timeline_includes_old_version() -> None:
    ids = [c.clause_id for c in _repo().version_timeline("TT22/Điều 1")]
    assert "TT41/Điều 6.3" in ids and "TT22/Điều 1" in ids
    # theo thứ tự thời gian: bản cũ (2016) trước bản mới (2023)
    timeline = _repo().version_timeline("TT22/Điều 1")
    assert timeline[0].clause_id == "TT41/Điều 6.3"


def test_export_graph_shape() -> None:
    g = _repo().export_graph()
    assert "nodes" in g and "edges" in g
    assert len(g["nodes"]) >= 1 and len(g["edges"]) >= 1
