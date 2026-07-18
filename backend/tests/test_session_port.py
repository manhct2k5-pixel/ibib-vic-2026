"""Test session_store + retrieve_session + PDF chunking (không cần DB/mạng)."""

from __future__ import annotations

from datetime import date

from backend.ingest.pdf_ingest import extract_metadata, split_into_clauses
from backend.kb.session_store import (
    SessionClause,
    clear_session,
    get_session_clauses,
    put_session_clauses,
)
from backend.pipeline.session_retrieve import retrieve_session
from backend.providers.llm import MockLLM


def _clause(cid, text, doc="TT99", path="Điều 1", vis="public"):
    return SessionClause(cid, doc, path, text, date(2025, 1, 1), visibility=vis)


def test_session_store_isolation():
    clear_session("A")
    clear_session("B")
    put_session_clauses("A", [_clause("TT99/Điều 1", "abc")])
    assert len(get_session_clauses("A")) == 1
    assert get_session_clauses("B") == []  # không rò sang phiên khác
    assert get_session_clauses("") == []


def test_retrieve_session_keyword_match():
    clauses = [
        _clause("TT99/Điều 1", "Tỷ lệ dự trữ bắt buộc là 3%"),
        _clause("TT99/Điều 2", "Quy định về nghỉ phép nhân viên"),
    ]
    hits = retrieve_session(clauses, "tỷ lệ dự trữ bắt buộc", date(2026, 1, 1))
    ids = {c.clause_id for c in hits}
    assert "TT99/Điều 1" in ids
    assert "TT99/Điều 2" not in ids


def test_retrieve_session_customer_hides_internal():
    clauses = [_clause("X/Điều 1", "chính sách nội bộ mật", vis="internal")]
    assert retrieve_session(clauses, "chính sách nội bộ", date(2026, 1, 1), "customer") == []
    assert len(retrieve_session(clauses, "chính sách nội bộ", date(2026, 1, 1), "employee")) == 1


def test_pdf_split_and_metadata_regex():
    text = (
        "THÔNG TƯ 88\nCó hiệu lực kể từ ngày 01 tháng 03 năm 2025.\n"
        "Điều 1. Phạm vi\nNội dung điều 1.\n"
        "Điều 2.3. Tỷ lệ\nNội dung điều 2.3.\n"
    )
    secs = split_into_clauses(text)
    assert [s["path"] for s in secs] == ["Điều 1", "Điều 2.3"]
    # MockLLM không trả JSON → rơi về regex 'hiệu lực ... ngày'
    meta = extract_metadata(MockLLM(), text)
    assert meta["effective_date"] == date(2025, 3, 1)
