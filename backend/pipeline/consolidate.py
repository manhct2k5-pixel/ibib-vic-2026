"""Văn bản hợp nhất (FR-17) — dựng bản hợp nhất một văn bản gốc trên KnowledgeBase.

Đọc READ-ONLY từ `KnowledgeBase`: gộp các điều khoản của `doc_code`, đánh dấu
active / superseded / amended dựa trên quan hệ SUPERSEDES/AMENDS trong đồ thị tri
thức + `kb.is_active(clause_id, as_of)` (AD-5, không viết lại luật hiệu lực).

Hỗ trợ trộn clause phiên (AD-13, Story 7.2/7.6) read-only: clause phiên cùng
`doc_code` được gộp vào (phiên đè global theo `clause_id`), luôn coi là đang hiệu
lực tại `effective_date` của nó (tài liệu đính kèm không suy quan hệ liên-văn-bản).

Fail-closed theo role: `customer` không thấy điều khoản `internal` (AD-11).
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional


def _natural_key(path: str) -> list[int]:
    """Sắp xếp 'Điều 6.3' < 'Điều 10' theo số, không theo chuỗi."""
    nums = [int(n) for n in re.findall(r"\d+", path or "")]
    return nums or [0]


def consolidate_document(
    kb: Any,
    doc_code: str,
    as_of: date,
    role: str = "employee",
    session_clauses: Optional[list] = None,
) -> dict:
    """Trả về bản hợp nhất của `doc_code` tại thời điểm `as_of`.

    Kết quả (JSON-serializable) khớp FE ConsolidatedDocView:
        {docCode, title, asOf, sections: [{path, clauseId, text, status,
         amendedBy, amendNote, amendedByText, amendedByPath, effectiveFrom,
         fromSession}]}
    status ∈ {active, amended, superseded, expired}.
    """
    is_public_only = role not in ("employee", "staff")

    # Điều khoản global thuộc doc_code
    base = {
        cid: c for cid, c in kb.clauses_dict.items() if c.doc_code == doc_code
    }
    # Clause phiên cùng doc_code — phiên ĐÈ global (AD-13)
    session_map: dict[str, Any] = {}
    if session_clauses:
        for c in session_clauses:
            if getattr(c, "doc_code", None) == doc_code:
                session_map[c.clause_id] = c
    merged = dict(base)
    merged.update(session_map)

    doc = kb.documents_dict.get(doc_code)
    title = doc.title if doc else doc_code
    if not doc and session_map:
        # tài liệu chỉ tồn tại ở phiên: lấy tiêu đề tạm từ doc_code
        title = f"{doc_code} (đính kèm phiên)"

    sections: list[dict] = []
    for cid, c in merged.items():
        visibility = getattr(c, "visibility", "public")
        if is_public_only and visibility == "internal":
            continue  # AD-11: khách hàng không thấy nội bộ

        from_session = cid in session_map
        # Clause phiên coi như đang hiệu lực; global soi is_active (AD-5)
        active = True if from_session else kb.is_active(cid, as_of)

        status = "active"
        amended_by: Optional[str] = None
        amend_note: Optional[str] = None
        amended_by_text: Optional[str] = None
        amended_by_path: Optional[str] = None

        # Quan hệ đến clause này (chỉ global có đồ thị; phiên không suy quan hệ)
        if not from_session and cid in kb.graph:
            for u, _v, data in kb.graph.in_edges(cid, data=True):
                etype = data.get("type")
                if etype not in ("SUPERSEDES", "AMENDS"):
                    continue
                src = kb.clauses_dict.get(u)
                if is_public_only and src and src.visibility == "internal":
                    continue  # không lộ văn bản nội bộ thay thế cho khách
                amended_by = u
                amend_note = data.get("note")
                if src is not None:
                    amended_by_text = src.text
                    amended_by_path = src.path
                if etype == "SUPERSEDES":
                    status = "superseded"
                elif status != "superseded":
                    status = "amended"

        if status == "active" and not active:
            status = "expired"

        sections.append(
            {
                "path": c.path,
                "clauseId": cid,
                "text": c.text,
                "status": status,
                "amendedBy": amended_by,
                "amendNote": amend_note,
                "amendedByText": amended_by_text,
                "amendedByPath": amended_by_path,
                "effectiveFrom": c.effective_date.isoformat(),
                "fromSession": from_session,
            }
        )

    sections.sort(key=lambda s: _natural_key(s["path"]))
    return {
        "docCode": doc_code,
        "title": title,
        "asOf": as_of.isoformat(),
        "sections": sections,
    }
