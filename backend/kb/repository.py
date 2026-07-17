"""Repository — ranh giới truy cập dữ liệu duy nhất (AD-12).

`StubRepository` đọc `corpus.json` vào RAM và hiện thực đầy đủ interface
`Repository` bằng Python thuần. Epic 0.4 sẽ thay bằng `PostgresRepository` với
CÙNG chữ ký (đổi ở `kb/factory.py`), không phải sửa pipeline/api.
"""

from __future__ import annotations

import json
import unicodedata
from datetime import date
from pathlib import Path

from .models import Clause, ConflictPair


class CorpusNotFoundError(FileNotFoundError):
    """Không tìm thấy / corpus rỗng khi khởi động (fail fast — AD-2)."""


def is_active(clause: Clause, as_of: date) -> bool:
    """Điều khoản còn hiệu lực tại `as_of` — ĐỊNH NGHĨA DUY NHẤT (AD-5).

    Nửa mở: `effective_date <= as_of AND (expiry_date IS NULL OR as_of < expiry_date)`.
    """
    return clause.effective_date <= as_of and (
        clause.expiry_date is None or as_of < clause.expiry_date
    )


def _norm(text: str) -> str:
    """Chuẩn hóa để so khớp từ khóa: thường hóa + bỏ dấu tiếng Việt."""
    text = text.lower().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _parse_clause(raw: dict) -> Clause:
    metric = raw.get("metric") or {}
    return Clause(
        clause_id=raw["clause_id"],
        doc_code=raw["doc_code"],
        path=raw["path"],
        body=raw["text"],
        effective_date=date.fromisoformat(raw["effective_date"]),
        expiry_date=_parse_date(raw.get("expiry_date")),
        topic=raw["topic"],
        visibility=raw["visibility"],
        metric_value=metric.get("value"),
        metric_unit=metric.get("unit"),
    )


class StubRepository:
    """Hiện thực `Repository` trên corpus trong RAM (tuân Protocol AD-12)."""

    def __init__(
        self,
        clauses: list[Clause],
        doc_titles: dict[str, str],
        edges: list[dict],
    ) -> None:
        self._clauses = clauses
        self._by_id = {c.clause_id: c for c in clauses}
        self._doc_titles = doc_titles
        self._edges = edges

    @classmethod
    def from_corpus(cls, path: str | Path) -> "StubRepository":
        p = Path(path)
        if not p.exists():
            raise CorpusNotFoundError(f"Không tìm thấy corpus tại: {p}")
        data = json.loads(p.read_text(encoding="utf-8"))
        clauses = [_parse_clause(c) for c in data.get("clauses", [])]
        if not clauses:
            raise CorpusNotFoundError(f"Corpus rỗng (không có clause): {p}")
        doc_titles = {d["doc_code"]: d["title"] for d in data.get("documents", [])}
        edges = list(data.get("edges", []))
        return cls(clauses, doc_titles, edges)

    # --- helper (ngoài Protocol, dùng cho endpoint green-pipe Story 1.1) ---
    def clause_count(self) -> int:
        return len(self._clauses)

    def doc_title(self, doc_code: str) -> str:
        return self._doc_titles.get(doc_code, doc_code)

    def any_clause(self) -> Clause:
        return self._clauses[0]

    # --- interface Repository (AD-12) ---
    def search(self, q: str, as_of: date, scope: str = "all") -> list[Clause]:
        terms = [t for t in _norm(q).split() if t]
        scored: list[tuple[int, Clause]] = []
        for c in self._clauses:
            if not is_active(c, as_of):
                continue
            if scope == "public" and c.visibility != "public":
                continue
            # Khớp theo TỪ (token), không substring — tránh false positive
            # kiểu "an"/"co" khớp lung tung, và gần hành vi Postgres FTS hơn (P3).
            hay_tokens = set(_norm(f"{c.body} {c.path} {c.doc_code}").split())
            hits = sum(1 for t in terms if t in hay_tokens)
            if hits:
                scored.append((hits, c))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [c for _, c in scored]

    def expand_references(
        self, clause_ids: list[str], scope: str = "all"
    ) -> list[Clause]:
        ids = set(clause_ids)
        out: list[Clause] = []
        for e in self._edges:
            if e.get("type") == "REFERENCES" and e.get("from") in ids:
                target = self._by_id.get(e.get("to"))
                if target is None or target in out:
                    continue
                if scope == "public" and target.visibility != "public":
                    continue  # không rò clause internal qua dẫn chiếu (AD-11)
                out.append(target)
        return out

    def find_conflicts(self, as_of: date, scope: str = "all") -> list[ConflictPair]:
        candidates = [
            c
            for c in self._clauses
            if is_active(c, as_of)
            and c.metric_value is not None
            # scope='public' → không so clause internal (AD-11, không rò cho khách hàng)
            and (scope != "public" or c.visibility == "public")
        ]
        pairs: list[ConflictPair] = []
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                a, b = candidates[i], candidates[j]
                if (
                    a.topic == b.topic
                    and a.metric_unit == b.metric_unit  # cùng đơn vị mới so được (P4)
                    and a.metric_value != b.metric_value
                ):
                    pairs.append(
                        ConflictPair(
                            clause_a=a,
                            clause_b=b,
                            topic=a.topic,
                            value_a=a.metric_value,
                            value_b=b.metric_value,
                            unit=a.metric_unit,
                        )
                    )
        return pairs

    def version_timeline(self, clause_id: str) -> list[Clause]:
        related = {clause_id}
        changed = True
        while changed:
            changed = False
            for e in self._edges:
                if e.get("type") != "SUPERSEDES":
                    continue
                a, b = e.get("from"), e.get("to")
                if a in related and b not in related:
                    related.add(b)
                    changed = True
                if b in related and a not in related:
                    related.add(a)
                    changed = True
        clauses = [self._by_id[cid] for cid in related if cid in self._by_id]
        return sorted(clauses, key=lambda c: c.effective_date)

    def export_graph(self, scope: str = "all") -> dict:
        # scope='public' → chỉ node public; edge chạm node internal bị loại (AD-11)
        visible = [
            c
            for c in self._clauses
            if scope != "public" or c.visibility == "public"
        ]
        visible_ids = {c.clause_id for c in visible}
        nodes = [
            {
                "id": c.clause_id,
                "doc_code": c.doc_code,
                "path": c.path,
                "topic": c.topic,
                "visibility": c.visibility,
                "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
            }
            for c in visible
        ]
        edges = [
            {"from": e.get("from"), "to": e.get("to"), "type": e.get("type")}
            for e in self._edges
            if e.get("from") in visible_ids and e.get("to") in visible_ids
        ]
        return {"nodes": nodes, "edges": edges}

    def insert_document(
        self, doc: dict, clauses: list[dict], edges: list[dict]
    ) -> None:
        # Stub: nạp vào RAM (KHÔNG bền vững). Bản Postgres (Epic 0/5) sẽ ghi bền.
        self._doc_titles[doc["doc_code"]] = doc["title"]
        for raw in clauses:
            clause = _parse_clause(raw)
            self._clauses.append(clause)
            self._by_id[clause.clause_id] = clause
        self._edges.extend(edges)
