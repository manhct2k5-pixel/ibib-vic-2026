"""Hợp đồng dữ liệu dùng chung giữa Epic 0 (Database) và Epic 1-6 (AD-12).

`Clause` là kiểu trả về ổn định của mọi hàm repository. Stub (Story 1.1) và
repository Postgres thật (Epic 0.4) PHẢI trả cùng kiểu này, cùng chữ ký hàm.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Clause:
    clause_id: str
    doc_code: str
    path: str
    body: str
    effective_date: date
    expiry_date: date | None
    topic: str
    visibility: str
    metric_value: float | None = None
    metric_unit: str | None = None


@dataclass(frozen=True)
class Source:
    """Một nguồn trích dẫn trả về cho frontend (khớp AD-6)."""

    clause_id: str
    name: str
    description: str


@dataclass(frozen=True)
class ConflictPair:
    """Một cặp điều khoản cùng chủ đề, cùng hiệu lực, khác giá trị số (FR-11)."""

    clause_a: Clause
    clause_b: Clause
    topic: str
    value_a: float | None
    value_b: float | None
    unit: str | None
