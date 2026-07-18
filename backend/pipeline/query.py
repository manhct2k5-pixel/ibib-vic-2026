"""Điều phối pipeline: retrieve -> expand, hợp nhất giữ thứ tự, khử trùng lặp.

Đây là "candidate set" mà stage synthesize (Story 1.5) sẽ đọc để tổng hợp câu
trả lời. Thứ tự stage theo AD-3.
"""

from __future__ import annotations

from datetime import date

from kb.models import Clause
from kb.repository_protocol import Repository

from .expand import expand
from .retrieve import retrieve


def gather_candidates(
    repo: Repository,
    question: str,
    as_of: date,
    scope: str = "all",
    mode: str = "system",
) -> list[Clause]:
    # Baseline (RAG thường, AD-3): CÙNG pipeline nhưng TẮT stage temporal + expand.
    # retrieve không lọc hiệu lực → thấy cả bản cũ; không kéo dẫn chiếu.
    if mode == "baseline":
        return retrieve(repo, question, as_of, scope, apply_temporal=False)

    found = retrieve(repo, question, as_of, scope)
    referenced = expand(repo, found, scope)

    # Hợp nhất giữ thứ tự: kết quả retrieve trước, điều dẫn chiếu thêm sau;
    # không trùng clause_id (FR-5).
    seen: set[str] = set()
    merged: list[Clause] = []
    for clause in [*found, *referenced]:
        if clause.clause_id not in seen:
            seen.add(clause.clause_id)
            merged.append(clause)
    return merged
