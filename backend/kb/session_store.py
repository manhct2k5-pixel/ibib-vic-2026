"""Kho tài liệu phiên (ephemeral, AD-13) — in-memory theo sessionId, KHÔNG persist.

Tài liệu nhân viên đính kèm trong chat KHÔNG đổ vào PostgreSQL global (dwh). Chúng
sống trong tiến trình theo `sessionId`, cap số phiên (evict cũ nhất), mất khi restart.

`SessionClause` là object nhẹ tương thích attr với `KnowledgeBase` Clause (.text,
.doc_code, .clause_id, .path, .effective_date, .visibility, ...) để `consolidate`
và `retrieve_session` dùng lại được mà không đụng ORM/DB.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

_MAX_SESSIONS = 50  # cap số phiên giữ đồng thời (evict LRU)

_store: "OrderedDict[str, list[SessionClause]]" = OrderedDict()


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


def put_session_clauses(session_id: str, clauses: list[SessionClause]) -> int:
    """Gộp thêm clause vào phiên (không persist). Trả tổng số clause của phiên."""
    if session_id in _store:
        _store.move_to_end(session_id)
        _store[session_id].extend(clauses)
    else:
        _store[session_id] = list(clauses)
        while len(_store) > _MAX_SESSIONS:
            _store.popitem(last=False)  # evict phiên cũ nhất
    return len(_store[session_id])


def get_session_clauses(session_id: str) -> list[SessionClause]:
    """Lấy clause của phiên (rỗng nếu không có). Không rò sang phiên khác."""
    if not session_id or session_id not in _store:
        return []
    _store.move_to_end(session_id)
    return list(_store[session_id])


def clear_session(session_id: str) -> None:
    _store.pop(session_id, None)
