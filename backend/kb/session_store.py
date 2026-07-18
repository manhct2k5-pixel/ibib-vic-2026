"""Kho tài liệu phiên (ephemeral, AD-13) — in-memory theo sessionId, KHÔNG persist.

Tài liệu nhân viên đính kèm trong chat KHÔNG đổ vào PostgreSQL global (dwh). Chúng
sống trong tiến trình theo `sessionId`, cap số phiên (evict cũ nhất), mất khi restart.

Lưu 3 thứ song song theo sessionId:
- clauses: list[SessionClause] — để retrieve/chat + consolidate (giữ API cũ).
- docs: dict[doc_code, SessionDoc] — metadata từng văn bản upload.
- relations: list[SessionRelation] — quan hệ liên-văn-bản (LLM/regex trích).

`SessionClause` tương thích attr với `KnowledgeBase` Clause (dùng .text) để
`consolidate` và `retrieve_session` dùng lại mà không đụng ORM/DB.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import date
from typing import Optional

_MAX_SESSIONS = 50  # cap số phiên giữ đồng thời (evict LRU)

_store: "OrderedDict[str, list[SessionClause]]" = OrderedDict()
_docs: "OrderedDict[str, dict[str, SessionDoc]]" = OrderedDict()
_relations: "OrderedDict[str, list[SessionRelation]]" = OrderedDict()


@dataclass
class SessionClause:
    """Điều khoản đính kèm phiên — tương thích attr với dwh Clause (dùng .text)."""

    clause_id: str
    doc_code: str
    path: str
    text: str
    effective_date: date
    expiry_date: Optional[date] = None
    topic: str = ""
    visibility: str = "public"
    status: str = "active"
    metric_value: Optional[float] = None
    metric_unit: Optional[str] = None
    department: str = "phap_ly"


@dataclass
class SessionDoc:
    """Metadata một văn bản upload (trích bằng LLM/regex).

    `raw_text` giữ phần đầu văn bản để phân tích LLM TRỄ (lúc gửi chat, không phải
    lúc upload). `analyzed` = đã chạy LLM trích quan hệ chưa.
    """

    doc_code: str
    title: str
    doc_type: str = ""  # Thông tư | Nghị định | Quyết định | VBHN | ...
    issuer: str = ""  # NHNN | Chính phủ | ...
    issue_date: Optional[date] = None
    effective_date: Optional[date] = None
    num_clauses: int = 0
    filename: str = ""
    raw_text: str = ""  # phần đầu văn bản (để phân tích LLM trễ)
    analyzed: bool = False


@dataclass
class SessionRelation:
    """Quan hệ liên-văn-bản trích từ nội dung tài liệu upload."""

    from_doc: str
    to_doc: str
    rel_type: str  # AMENDS | SUPERSEDES | REFERENCES | GUIDES | CONSOLIDATES
    from_article: Optional[str] = None
    to_article: Optional[str] = None
    note: Optional[str] = None
    to_in_session: bool = False  # target có nằm trong các doc đã upload không


def _touch(session_id: str) -> None:
    for od in (_store, _docs, _relations):
        if session_id in od:
            od.move_to_end(session_id)


def _evict() -> None:
    while len(_store) > _MAX_SESSIONS:
        old, _ = _store.popitem(last=False)
        _docs.pop(old, None)
        _relations.pop(old, None)


def put_session_clauses(session_id: str, clauses: list[SessionClause]) -> int:
    """Gộp thêm clause vào phiên (không persist). Trả tổng số clause của phiên."""
    if session_id in _store:
        _store.move_to_end(session_id)
        _store[session_id].extend(clauses)
    else:
        _store[session_id] = list(clauses)
        _evict()
    return len(_store[session_id])


def get_session_clauses(session_id: str) -> list[SessionClause]:
    """Lấy clause của phiên (rỗng nếu không có). Không rò sang phiên khác."""
    if not session_id or session_id not in _store:
        return []
    _store.move_to_end(session_id)
    return list(_store[session_id])


def put_session_doc(
    session_id: str, doc: SessionDoc, relations: Optional[list[SessionRelation]] = None
) -> None:
    """Lưu metadata 1 văn bản + quan hệ của nó vào phiên (doc_code đè)."""
    if session_id not in _store:
        _store[session_id] = []
        _evict()
    _docs.setdefault(session_id, {})[doc.doc_code] = doc
    if relations:
        _relations.setdefault(session_id, []).extend(relations)
    _touch(session_id)


def get_session_docs(session_id: str) -> list[SessionDoc]:
    if not session_id or session_id not in _docs:
        return []
    _touch(session_id)
    return list(_docs[session_id].values())


def get_session_relations(session_id: str) -> list[SessionRelation]:
    if not session_id or session_id not in _relations:
        return []
    _touch(session_id)
    return list(_relations[session_id])


def remove_session_doc(session_id: str, doc_code: str) -> bool:
    """Xoá 1 văn bản khỏi phiên: bỏ metadata + clause + quan hệ xuất phát từ nó.

    Trả True nếu có xoá được văn bản. Quan hệ tới văn bản khác (to_doc) được giữ
    nếu văn bản nguồn còn; chỉ bỏ quan hệ mà from_doc == doc_code.
    """
    docs = _docs.get(session_id)
    if not docs or doc_code not in docs:
        return False
    del docs[doc_code]
    if session_id in _store:
        _store[session_id] = [
            c for c in _store[session_id] if c.doc_code != doc_code
        ]
    if session_id in _relations:
        _relations[session_id] = [
            r for r in _relations[session_id] if r.from_doc != doc_code
        ]
    _touch(session_id)
    return True


def clear_session(session_id: str) -> None:
    _store.pop(session_id, None)
    _docs.pop(session_id, None)
    _relations.pop(session_id, None)
