"""Retrieve trên tài liệu phiên (ephemeral, AD-13) — overlay read-only cho chat.

Tài liệu nhân viên đính kèm KHÔNG nằm trong KnowledgeBase (DB global). Đây là lớp
khớp từ khóa mỏng để đưa Điều/Khoản liên quan của tài liệu phiên vào tập ứng viên
trước khi synthesize. Tái dùng `tokenize_vietnamese` của KnowledgeBase cho nhất quán.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.kb.kb import tokenize_vietnamese
from backend.kb.session_store import SessionClause


def _is_active(clause: SessionClause, as_of: date) -> bool:
    """Luật hiệu lực AD-5 áp cho clause phiên (expiry thường None → luôn active)."""
    if clause.effective_date > as_of:
        return False
    if clause.expiry_date and as_of >= clause.expiry_date:
        return False
    return True


def retrieve_session(
    session_clauses: list[SessionClause],
    question: str,
    as_of: date,
    role: str = "employee",
    apply_temporal: bool = True,
) -> list[SessionClause]:
    """Khớp từ khóa câu hỏi với clause phiên. Fail-closed theo role (AD-11)."""
    terms = set(tokenize_vietnamese(question))
    if not terms:
        return []
    is_public_only = role not in ("employee", "staff")
    out: list[SessionClause] = []
    for c in session_clauses:
        if is_public_only and c.visibility == "internal":
            continue  # khách hàng không thấy clause phiên nội bộ
        if apply_temporal and not _is_active(c, as_of):
            continue
        hay = set(tokenize_vietnamese(f"{c.text} {c.path} {c.doc_code}"))
        if terms & hay:
            out.append(c)
    return out
