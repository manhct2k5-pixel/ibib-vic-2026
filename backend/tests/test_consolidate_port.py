"""Test consolidate_document trên base KnowledgeBase (fake KB, không cần DB)."""

from __future__ import annotations

from datetime import date

import networkx as nx

from backend.pipeline.consolidate import consolidate_document


class _Clause:
    def __init__(
        self, clause_id, doc_code, path, text, eff, exp=None, visibility="public"
    ):
        self.clause_id = clause_id
        self.doc_code = doc_code
        self.path = path
        self.text = text
        self.effective_date = eff
        self.expiry_date = exp
        self.visibility = visibility


class _Doc:
    def __init__(self, doc_code, title, eff):
        self.doc_code = doc_code
        self.title = title
        self.effective_date = eff


class _KB:
    def __init__(self):
        self.clauses_dict = {}
        self.documents_dict = {}
        self.graph = nx.DiGraph()

    def is_active(self, clause_id, as_of):
        c = self.clauses_dict.get(clause_id)
        if not c:
            return False
        if c.effective_date > as_of:
            return False
        if c.expiry_date and as_of >= c.expiry_date:
            return False
        return True


def _kb():
    kb = _KB()
    kb.documents_dict["TT41"] = _Doc("TT41", "Thông tư 41", date(2016, 1, 1))
    # Điều 6.3 (CAR 8%) bị TT22/Điều 1 thay thế; Điều 8.1 còn hiệu lực
    kb.clauses_dict["TT41/Điều 6.3"] = _Clause(
        "TT41/Điều 6.3", "TT41", "Điều 6.3", "CAR 8%", date(2016, 1, 1), date(2023, 1, 1)
    )
    kb.clauses_dict["TT41/Điều 8.1"] = _Clause(
        "TT41/Điều 8.1", "TT41", "Điều 8.1", "Báo cáo", date(2016, 1, 1)
    )
    kb.clauses_dict["TT41/Điều 2"] = _Clause(
        "TT41/Điều 2", "TT41", "Điều 2", "Nội bộ", date(2016, 1, 1), visibility="internal"
    )
    kb.clauses_dict["TT22/Điều 1"] = _Clause(
        "TT22/Điều 1", "TT22", "Điều 1", "CAR 9%", date(2023, 1, 1)
    )
    kb.graph.add_edge(
        "TT22/Điều 1", "TT41/Điều 6.3", type="SUPERSEDES", note="Nâng CAR 8%→9%"
    )
    return kb


def test_consolidate_marks_superseded():
    kb = _kb()
    r = consolidate_document(kb, "TT41", date(2026, 7, 18), "employee")
    by_path = {s["path"]: s for s in r["sections"]}
    assert by_path["Điều 6.3"]["status"] == "superseded"
    assert by_path["Điều 6.3"]["amendedBy"] == "TT22/Điều 1"
    assert by_path["Điều 8.1"]["status"] == "active"


def test_consolidate_customer_hides_internal():
    kb = _kb()
    r = consolidate_document(kb, "TT41", date(2026, 7, 18), "customer")
    paths = {s["path"] for s in r["sections"]}
    assert "Điều 2" not in paths  # internal ẩn với khách (AD-11)
    assert "Điều 8.1" in paths


def test_consolidate_natural_sort():
    kb = _kb()
    r = consolidate_document(kb, "TT41", date(2026, 7, 18), "employee")
    paths = [s["path"] for s in r["sections"]]
    # 'Điều 2' < 'Điều 6.3' < 'Điều 8.1' theo số (không phải chuỗi)
    assert paths == ["Điều 2", "Điều 6.3", "Điều 8.1"]


def test_consolidate_merges_session_clause():
    from backend.kb.session_store import SessionClause

    kb = _kb()
    sc = [
        SessionClause(
            "TT41/Điều 99", "TT41", "Điều 99", "Điều bổ sung phiên",
            date(2025, 1, 1),
        )
    ]
    r = consolidate_document(kb, "TT41", date(2026, 7, 18), "employee", sc)
    by_path = {s["path"]: s for s in r["sections"]}
    assert by_path["Điều 99"]["fromSession"] is True
    assert by_path["Điều 99"]["status"] == "active"
