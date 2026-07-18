"""Phân tích bộ tài liệu upload theo phiên → bản đồ quan hệ + thứ tự đọc + hướng
dẫn đọc (FR-17, MVP chỉ dùng dữ liệu upload).

Đầu vào: các `SessionDoc` + `SessionRelation` đã trích ở khâu upload (doc_analyze).
Đầu ra (JSON cho FE): documents, graph{nodes,edges}, readingOrder[], guide (văn xuôi).

Không gọi LLM ở đây (nhanh, tất định); hướng dẫn đọc dựng theo luật đơn giản dựa
trên loại quan hệ (CONSOLIDATES/AMENDS/SUPERSEDES/REFERENCES/GUIDES).
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from backend.providers.llm import get_llm, is_configured

_MAX_LLM_MERGES = 8  # chặn trần số lời gọi LLM/1 văn bản hợp nhất (giới hạn độ trễ)


def _norm_path(p: str) -> str:
    """Chuẩn hoá 'Điều 22' để so khớp article (bỏ dấu cách thừa, thường hoá)."""
    return re.sub(r"\s+", " ", (p or "").strip().lower())


def _amending_text(clauses: list, from_doc: str, to_article: Optional[str]) -> str:
    """Gom nội dung điều khoản của VĂN BẢN SỬA ĐỔI (from_doc). Ưu tiên clause nhắc
    tới đúng Điều bị sửa; nếu không thì lấy toàn bộ (cap độ dài)."""
    doc_clauses = [c for c in clauses if c.doc_code == from_doc]
    if to_article:
        nums = re.findall(r"\d+", to_article)
        if nums:
            focused = [c for c in doc_clauses if nums[0] in (c.text or "")]
            if focused:
                doc_clauses = focused
    return "\n".join(f"[{c.path}] {c.text}" for c in doc_clauses)[:3000]


def _llm_merge_clause(
    clause_id: str, original: str, amending_text: str, amend_note: Optional[str]
) -> Optional[dict]:
    """LLM sinh VĂN BẢN HỢP NHẤT của một Điều: áp sửa đổi vào điều gốc, tự khớp
    Khoản/Điểm. Trả {consolidated, changes} hoặc None (lỗi → giữ text gốc)."""
    if not is_configured():
        return None
    system = (
        "Bạn tạo VĂN BẢN HỢP NHẤT pháp lý Việt Nam. Cho ĐIỀU GỐC và NỘI DUNG SỬA "
        "ĐỔI, hãy viết lại toàn văn Điều đã ÁP DỤNG sửa đổi: giữ nguyên phần không "
        "đổi, chỉ thay/bổ sung/bãi bỏ đúng Khoản/Điểm bị sửa. CHỈ trả JSON: "
        '{"consolidated": "<toàn văn Điều sau hợp nhất>", "changes": "<1 câu tóm '
        'tắt phần đã thay đổi>"}. KHÔNG bịa, chỉ dùng nội dung được cung cấp. Thiếu '
        "thông tin để hợp nhất → consolidated = nguyên văn Điều gốc."
    )
    prompt = (
        f"ĐIỀU GỐC [{clause_id}]:\n{original}\n\n"
        f"NỘI DUNG SỬA ĐỔI:\n{amending_text}\n"
        f"Ghi chú sửa đổi: {amend_note or '(không có)'}\n\nTrả JSON:"
    )
    try:
        raw = get_llm().generate(system, prompt, timeout=25)
        s, e = raw.find("{"), raw.rfind("}")
        if s == -1 or e == -1:
            return None
        obj = json.loads(raw[s : e + 1])
        merged = str(obj.get("consolidated") or "").strip()
        return {"consolidated": merged, "changes": str(obj.get("changes") or "").strip()} if merged else None
    except Exception:  # noqa: BLE001 — lỗi LLM → giữ text gốc
        return None


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
    docs: list, relations: list, clauses: list, as_of, llm_merge: bool = True
) -> dict:
    """Dựng MỘT văn bản hợp nhất tổng hợp quanh văn bản nền (primary): liệt kê các
    điều của bản nền; điều bị sửa đổi được LLM ÁP nội dung sửa vào điều gốc → sinh
    `consolidatedText` (đọc liền mạch) + trace-back, giữ cả `text` gốc để đối chiếu."""
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
    merges_done = 0
    for c in sorted(base_clauses, key=_key):
        art = _norm_path(c.path)
        # ưu tiên sửa đổi đúng Điều; nếu không có Điều thì áp dụng mức văn bản
        hit = next(
            (r for r in amend_rels if r.to_article and _norm_path(r.to_article) == art),
            None,
        )
        status = "amended" if hit else "active"

        consolidated_text = None
        change_summary = None
        amending_text = None
        if hit:
            amending_text = _amending_text(clauses, hit.from_doc, hit.to_article)
            # LLM áp sửa đổi vào điều gốc (giới hạn số lần gọi)
            if llm_merge and merges_done < _MAX_LLM_MERGES:
                merged = _llm_merge_clause(c.clause_id, c.text, amending_text, hit.note)
                merges_done += 1
                if merged:
                    consolidated_text = merged["consolidated"]
                    change_summary = merged["changes"]

        sections.append({
            "path": c.path,
            "clauseId": c.clause_id,
            "text": c.text,  # nguyên văn Điều gốc (để đối chiếu cũ/mới)
            "consolidatedText": consolidated_text,  # bản đã áp sửa đổi (đọc chính)
            "changeSummary": change_summary,  # tóm tắt phần đã thay đổi
            "status": status,
            "amendedBy": hit.from_doc if hit else None,
            "amendNote": hit.note if hit else None,
            "amendedByText": amending_text,  # nội dung văn bản sửa đổi
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
