"""Stage retrieve — điều phối `repository.search` (AD-3).

Không viết SQL, không chạm DB trực tiếp: chỉ gọi repository (AD-7, AD-12).
Lọc hiệu lực (as-of) + visibility đã nằm trong `repository.search` (AD-5, AD-11).
"""

from __future__ import annotations

from datetime import date

from kb.models import Clause
from kb.repository_protocol import Repository


def retrieve(
    repo: Repository,
    question: str,
    as_of: date,
    scope: str = "all",
    apply_temporal: bool = True,
) -> list[Clause]:
    return repo.search(question, as_of, scope, apply_temporal)
