"""Phân tích bộ tài liệu upload theo phiên → bản đồ quan hệ + thứ tự đọc + hướng
dẫn đọc (FR-17, MVP chỉ dùng dữ liệu upload).

Đầu vào: các `SessionDoc` + `SessionRelation` đã trích ở khâu upload (doc_analyze).
Đầu ra (JSON cho FE): documents, graph{nodes,edges}, readingOrder[], guide (văn xuôi).

Không gọi LLM ở đây (nhanh, tất định); hướng dẫn đọc dựng theo luật đơn giản dựa
trên loại quan hệ (CONSOLIDATES/AMENDS/SUPERSEDES/REFERENCES/GUIDES).
"""

from __future__ import annotations

import re
from typing import Any


def _norm_path(p: str) -> str:
    """Chuẩn hoá 'Điều 22' để so khớp article (bỏ dấu cách thừa, thường hoá)."""
    return re.sub(r"\s+", " ", (p or "").strip().lower())


def pick_primary_doc(docs: list, relations: list) -> str | None:
    """Chọn văn bản 'trung tâm' để hợp nhất: ưu tiên VBHN (đã hợp nhất) → văn bản
    bị sửa đổi/thay thế trong phiên (bản gốc) → văn bản nhiều điều nhất."""
    if not docs:
        return None
    in_session = {d.doc_code for d in docs}
    consolidators = [
        r.from_doc for r in relations
        if r.rel_type == "CONSOLIDATES" and r.from_doc in in_session
    ]
    if consolidators:
        return consolidators[0]
    amended = [
        r.to_doc for r in relations
        if r.rel_type in ("AMENDS", "SUPERSEDES") and r.to_doc in in_session
    ]
    if amended:
        return amended[0]
    return max(docs, key=lambda d: d.num_clauses).doc_code


def build_session_consolidated(
    docs: list, relations: list, clauses: list, as_of
) -> dict:
    """Dựng MỘT văn bản hợp nhất tổng hợp quanh văn bản nền (primary): liệt kê các
    điều của bản nền, đánh dấu điều nào bị văn bản khác trong phiên sửa đổi."""
    primary = pick_primary_doc(docs, relations)
    if not primary:
        return {"docCode": None, "sections": []}
    doc_by_code = {d.doc_code: d for d in docs}
    pdoc = doc_by_code.get(primary)

    # Quan hệ sửa đổi/thay thế TRỎ VÀO bản nền
    amend_rels = [
        r for r in relations
        if r.to_doc == primary and r.rel_type in ("AMENDS", "SUPERSEDES")
    ]
    merged_from = sorted({r.from_doc for r in amend_rels})

    base_clauses = [c for c in clauses if c.doc_code == primary]

    def _key(c):
        nums = [int(n) for n in re.findall(r"\d+", c.path or "")]
        return nums or [0]

    sections = []
    for c in sorted(base_clauses, key=_key):
        art = _norm_path(c.path)
        # ưu tiên sửa đổi đúng Điều; nếu không có Điều thì áp dụng mức văn bản
        hit = next(
            (r for r in amend_rels if r.to_article and _norm_path(r.to_article) == art),
            None,
        )
        status = "amended" if hit else "active"
        sections.append({
            "path": c.path,
            "clauseId": c.clause_id,
            "text": c.text,
            "status": status,
            "amendedBy": hit.from_doc if hit else None,
            "amendNote": hit.note if hit else None,
            "amendedByText": None,
            "amendedByPath": hit.to_article if hit else None,
            "effectiveFrom": c.effective_date.isoformat() if c.effective_date else "",
            "fromSession": True,
        })

    # Sửa đổi mức văn bản (không nêu rõ Điều) → gộp thành ghi chú đầu
    doc_level = [r for r in amend_rels if not r.to_article]

    return {
        "docCode": primary,
        "title": pdoc.title if pdoc else primary,
        "asOf": as_of.isoformat(),
        "mergedFrom": merged_from,
        "docLevelNotes": [
            {"from": r.from_doc, "type": r.rel_type, "note": r.note}
            for r in doc_level
        ],
        "sections": sections,
    }

# Vai trò đọc theo mức ưu tiên (nhỏ = đọc trước)
_ROLE_ORDER = {
    "consolidated": 0,   # văn bản hợp nhất — đọc trước (bản gộp hiện hành)
    "current": 1,        # văn bản độc lập còn hiệu lực
    "amended": 2,        # văn bản gốc bị sửa đổi (đọc kèm để hiểu lịch sử)
    "historical": 3,     # đã bị thay thế/hợp nhất vào bản khác
    "external": 4,       # tài liệu tham chiếu ngoài (chưa upload) — nền tảng
}
_ROLE_LABEL = {
    "consolidated": "Văn bản hợp nhất (đọc trước — bản gộp hiện hành)",
    "current": "Văn bản hiện hành",
    "amended": "Văn bản gốc đã bị sửa đổi",
    "historical": "Văn bản đã bị thay thế / được hợp nhất",
    "external": "Tài liệu tham chiếu (chưa đính kèm)",
}


def build_session_analysis(docs: list, relations: list) -> dict:
    in_session = {d.doc_code for d in docs}

    # Phân loại vai trò từng văn bản đã upload theo quan hệ
    consolidates: set[str] = set()   # doc là VBHN (đi hợp nhất doc khác)
    superseded: set[str] = set()     # doc bị thay thế/hợp nhất bởi doc khác
    amended: set[str] = set()        # doc gốc bị sửa đổi
    for r in relations:
        if r.rel_type == "CONSOLIDATES":
            if r.from_doc in in_session:
                consolidates.add(r.from_doc)
            if r.to_doc in in_session:
                superseded.add(r.to_doc)
        elif r.rel_type == "SUPERSEDES":
            if r.to_doc in in_session:
                superseded.add(r.to_doc)
        elif r.rel_type == "AMENDS":
            if r.to_doc in in_session:
                amended.add(r.to_doc)

    def _role(code: str) -> str:
        if code not in in_session:
            return "external"
        if code in consolidates:
            return "consolidated"
        if code in superseded:
            return "historical"
        if code in amended:
            return "amended"
        return "current"

    # Nodes: văn bản upload + văn bản đích ngoài phiên (tham chiếu)
    doc_by_code = {d.doc_code: d for d in docs}
    ext_targets: dict[str, str] = {}  # code -> note/label gợi ý
    for r in relations:
        if r.to_doc not in in_session and r.to_doc not in ext_targets:
            ext_targets[r.to_doc] = r.note or ""

    nodes: list[dict] = []
    for d in docs:
        role = _role(d.doc_code)
        nodes.append({
            "id": d.doc_code,
            "label": d.doc_code,
            "title": d.title,
            "docType": d.doc_type,
            "issuer": d.issuer,
            "effectiveDate": d.effective_date.isoformat() if d.effective_date else None,
            "numClauses": d.num_clauses,
            "inSession": True,
            "role": role,
        })
    for code, note in ext_targets.items():
        nodes.append({
            "id": code,
            "label": code,
            "title": note,
            "docType": "",
            "issuer": "",
            "effectiveDate": None,
            "numClauses": 0,
            "inSession": False,
            "role": "external",
        })

    edges = [
        {
            "from": r.from_doc,
            "to": r.to_doc,
            "type": r.rel_type,
            "fromArticle": r.from_article,
            "toArticle": r.to_article,
            "note": r.note,
        }
        for r in relations
    ]

    # Thứ tự đọc: theo vai trò, rồi theo ngày hiệu lực (mới→cũ trong cùng nhóm)
    def _sort_key(code: str):
        role = _role(code)
        d = doc_by_code.get(code)
        eff = d.effective_date.isoformat() if d and d.effective_date else ""
        return (_ROLE_ORDER[role], eff and "0" or "1", eff)

    reading_order = []
    for code in sorted(in_session | set(ext_targets), key=_sort_key):
        role = _role(code)
        d = doc_by_code.get(code)
        reading_order.append({
            "docCode": code,
            "title": d.title if d else ext_targets.get(code, ""),
            "role": role,
            "roleLabel": _ROLE_LABEL[role],
            "inSession": code in in_session,
        })

    guide = _build_guide(docs, relations, consolidates, superseded, amended, ext_targets)

    return {
        "documents": [n for n in nodes if n["inSession"]],
        "graph": {"nodes": nodes, "edges": edges},
        "readingOrder": reading_order,
        "guide": guide,
        "primaryDoc": pick_primary_doc(docs, relations),
    }


def _build_guide(
    docs: list,
    relations: list,
    consolidates: set,
    superseded: set,
    amended: set,
    ext_targets: dict,
) -> str:
    """Hướng dẫn đọc dạng văn xuôi (rule-based, markdown nhẹ)."""
    if not docs:
        return "Chưa có tài liệu nào được đính kèm trong phiên."

    lines: list[str] = []
    lines.append(f"Đã phân tích **{len(docs)}** tài liệu đính kèm với "
                 f"**{len(relations)}** quan hệ liên văn bản.")

    # Ưu tiên nêu văn bản hợp nhất
    for d in docs:
        if d.doc_code in consolidates:
            merged = [r.to_doc for r in relations
                      if r.from_doc == d.doc_code and r.rel_type == "CONSOLIDATES"]
            lines.append(
                f"- **{d.doc_code}** — *{d.title}* là **văn bản hợp nhất**: đã gộp "
                f"{len(merged)} văn bản gốc/sửa đổi ({', '.join(merged[:6])}"
                f"{'…' if len(merged) > 6 else ''}). **Hãy đọc văn bản này trước** vì "
                f"nó là bản tổng hợp hiện hành; không cần đọc riêng từng văn bản cũ."
            )

    # Nêu quan hệ sửa đổi giữa các văn bản trong phiên
    for r in relations:
        if r.rel_type in ("AMENDS", "SUPERSEDES") and r.to_doc in {d.doc_code for d in docs}:
            verb = "sửa đổi" if r.rel_type == "AMENDS" else "thay thế"
            art = f" {r.to_article}" if r.to_article else ""
            lines.append(
                f"- **{r.from_doc}** {verb} **{r.to_doc}**{art}"
                f"{' — ' + r.note if r.note else ''}. Đọc {r.to_doc} trước để hiểu gốc, "
                f"rồi đối chiếu {r.from_doc}."
            )

    # Văn bản độc lập
    standalone = [d for d in docs
                  if d.doc_code not in consolidates and d.doc_code not in superseded
                  and d.doc_code not in amended]
    if standalone:
        codes = ", ".join(d.doc_code for d in standalone)
        lines.append(f"- Văn bản độc lập (đọc theo nhu cầu): {codes}.")

    if ext_targets:
        lines.append(
            f"- Tham chiếu ngoài (chưa đính kèm, là căn cứ pháp lý nền): "
            f"{', '.join(list(ext_targets)[:6])}"
            f"{'…' if len(ext_targets) > 6 else ''}."
        )
    return "\n".join(lines)
