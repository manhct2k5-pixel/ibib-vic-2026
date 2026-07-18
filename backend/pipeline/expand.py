"""Stage expand — kéo thêm điều được dẫn chiếu qua `repository.expand_references`.

Chỉ gọi repository (AD-7, AD-12).
"""

from __future__ import annotations

from kb.models import Clause
from kb.repository_protocol import Repository


def expand(
    repo: Repository, clauses: list[Clause], scope: str = "all"
) -> list[Clause]:
    return repo.expand_references([c.clause_id for c in clauses], scope)
