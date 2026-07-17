"""Hợp đồng interface Repository (AD-12) — ranh giới truy cập dữ liệu duy nhất.

`StubRepository` (Story 1.2) và `PostgresRepository` (Epic 0.4) đều PHẢI tuân
Protocol này. `pipeline`/`api` chỉ khai kiểu `Repository`, không biết phía sau
là RAM hay Postgres. Đổi phía sau (factory) không đụng phía trước.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from .models import Clause, ConflictPair


class Repository(Protocol):
    def clause_count(self) -> int:
        """Số điều khoản đang có (dùng cho /health)."""
        ...

    def search(
        self,
        q: str,
        as_of: date,
        scope: str = "all",
        apply_temporal: bool = True,
    ) -> list[Clause]:
        """Tìm điều khoản khớp `q`, CÒN HIỆU LỰC tại `as_of` (AD-5).
        scope='public' → chỉ trả clause `visibility='public'` (AD-11);
        scope='all' → mọi visibility. Kết quả sắp theo độ liên quan giảm dần.
        apply_temporal=False → baseline: bỏ lọc hiệu lực (thấy cả bản hết hạn)."""
        ...

    def expand_references(
        self, clause_ids: list[str], scope: str = "all"
    ) -> list[Clause]:
        """Trả các điều khoản được `clause_ids` DẪN CHIẾU (cạnh REFERENCES).
        scope='public' → không kéo clause `internal` (AD-11)."""
        ...

    def find_conflicts(self, as_of: date, scope: str = "all") -> list[ConflictPair]:
        """Các cặp điều khoản cùng `topic`, cùng còn hiệu lực, khác giá trị số.
        scope='public' → không so clause `internal` (AD-11)."""
        ...

    def version_timeline(self, clause_id: str) -> list[Clause]:
        """Chuỗi phiên bản (SUPERSEDES) liên quan tới `clause_id`, theo thời gian."""
        ...

    def export_graph(self, scope: str = "all") -> dict:
        """Đồ thị `{"nodes": [...], "edges": [...]}` cho trực quan (FR-12).
        scope='public' → bỏ node `internal` và mọi edge chạm node internal (AD-11)."""
        ...

    def insert_document(
        self, doc: dict, clauses: list[dict], edges: list[dict]
    ) -> None:
        """Nạp một văn bản mới (Admin — FR-3). Bản Postgres sẽ ghi bền vững."""
        ...
