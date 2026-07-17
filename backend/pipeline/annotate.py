"""Gắn trạng thái hiệu lực cho từng ứng viên (Story 1.4).

Mỗi ứng viên biết mình còn hiệu lực tại as-of không, và nếu không thì bản nào
đã thay thế nó (suy từ `repository.version_timeline`). Dùng cho FR-9 + đánh dấu
điều dẫn chiếu đã hết hiệu lực (follow-up Story 1.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from kb.models import Clause
from kb.repository import is_active  # AD-5: một nguồn logic hiệu lực duy nhất
from kb.repository_protocol import Repository


@dataclass(frozen=True)
class CandidateView:
    clause: Clause
    is_current: bool
    superseded_by: str | None


def annotate(
    repo: Repository, clauses: list[Clause], as_of: date, scope: str = "all"
) -> list[CandidateView]:
    views: list[CandidateView] = []
    for clause in clauses:
        current = is_active(clause, as_of)
        superseded_by: str | None = None
        if not current:
            # Bản thay thế = phiên bản ĐẾN SAU (effective_date >= clause) còn hiệu
            # lực tại as-of; chọn bản MỚI NHẤT (đúng cho chuỗi >2 phiên bản, P5).
            # scope=public → không lộ clause_id nội bộ qua superseded_by (AD-11).
            successors = [
                o
                for o in repo.version_timeline(clause.clause_id)
                if o.clause_id != clause.clause_id
                and o.effective_date >= clause.effective_date
                and is_active(o, as_of)
                and (scope != "public" or o.visibility == "public")
            ]
            if successors:
                superseded_by = max(
                    successors, key=lambda o: o.effective_date
                ).clause_id
        views.append(
            CandidateView(
                clause=clause, is_current=current, superseded_by=superseded_by
            )
        )
    return views
