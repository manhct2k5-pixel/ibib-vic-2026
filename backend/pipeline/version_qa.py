"""Định tuyến truy vấn theo ý định + hỏi–đáp theo phiên bản (lấy ý từ VersionRAG).

3 loại ý định:
- content : hỏi nội dung quy định (mặc định) → pipeline thường.
- version : liệt kê các phiên bản của một quy định qua thời gian.
- change  : hỏi quy định đã THAY ĐỔI thế nào giữa các phiên bản (diff + giải thích).

Khác VersionRAG (technical docs, số phiên bản): ta dùng CHUỖI QUAN HỆ pháp lý
SUPERSEDES/AMENDS + hiệu lực theo NGÀY để xác định phiên bản.
"""

from __future__ import annotations

import re
from datetime import date

from backend.providers.llm import get_llm, is_configured

_CHANGE_KW = [
    "thay đổi", "thay đổi thế nào", "sửa đổi thế nào", "khác gì", "khác nhau",
    "đã đổi", "đổi từ", "cập nhật gì", "có gì mới", "tăng hay giảm", "so với trước",
    "so với cũ", "bị bãi bỏ", "bị bỏ", "trước đây", "chênh lệch",
]
_VERSION_KW = [
    "các phiên bản", "phiên bản nào", "liệt kê", "có mấy phiên bản", "bao nhiêu phiên bản",
    "qua các thời kỳ", "dòng thời gian", "timeline", "lịch sử", "các lần sửa",
]


def _regex_intent(question: str) -> str:
    q = question.lower()
    if any(k in q for k in _CHANGE_KW):
        return "change"
    if any(k in q for k in _VERSION_KW):
        return "version"
    return "content"


def classify_intent(question: str) -> str:
    """Phân loại ý định. LLM trước (nếu có key), regex fallback."""
    rx = _regex_intent(question)
    if rx != "content":  # regex có tín hiệu rõ → tin ngay (nhanh, chắc)
        return rx
    if not is_configured():
        return "content"
    system = (
        "Phân loại câu hỏi pháp lý thành đúng 1 nhãn (chỉ trả 1 từ): "
        "content = hỏi nội dung/quy định hiện hành; "
        "version = liệt kê các phiên bản/lịch sử của một quy định; "
        "change = hỏi quy định đã THAY ĐỔI/khác gì giữa các phiên bản."
    )
    try:
        raw = get_llm().generate(system, f"Câu hỏi: {question}\nNhãn:", timeout=8).lower()
        for label in ("change", "version", "content"):
            if label in raw:
                return label
    except Exception:  # noqa: BLE001 — lỗi LLM → dùng regex
        pass
    return "content"


def version_chain(kb, clause_id: str) -> list:
    """Chuỗi phiên bản của một điều khoản: mọi điều nối bằng SUPERSEDES/AMENDS
    (hai chiều), sắp theo ngày hiệu lực (cũ → mới)."""
    if clause_id not in kb.clauses_dict:
        return []
    seen = {clause_id}
    frontier = [clause_id]
    while frontier:
        cid = frontier.pop()
        if cid not in kb.graph:
            continue
        edges = list(kb.graph.in_edges(cid, data=True)) + list(
            kb.graph.out_edges(cid, data=True)
        )
        for u, v, d in edges:
            if d.get("type") in ("SUPERSEDES", "AMENDS"):
                other = u if v == cid else v
                if other not in seen and other in kb.clauses_dict:
                    seen.add(other)
                    frontier.append(other)
    chain = [kb.clauses_dict[c] for c in seen]
    chain.sort(key=lambda c: c.effective_date)
    return chain


def _fmt_metric(c) -> str:
    if c.metric_value is not None:
        return f"{c.metric_value:g}{c.metric_unit or ''}"
    return ""


def build_version_answer(chain: list, as_of: date) -> str | None:
    """Liệt kê các phiên bản (markdown)."""
    if len(chain) < 2:
        return None
    lines = ["## Các phiên bản của quy định qua thời gian"]
    for c in chain:
        active = c.effective_date <= as_of and (c.expiry_date is None or as_of < c.expiry_date)
        metric = _fmt_metric(c)
        period = f"hiệu lực từ {c.effective_date}"
        if c.expiry_date:
            period += f" đến {c.expiry_date}"
        status = "hiện hành" if active else "đã hết hiệu lực / bị thay thế"
        m = f" — **{metric}**" if metric else ""
        lines.append(f"- **[{c.clause_id}]**{m} · {period} ({status})")
    return "\n".join(lines)


def build_change_answer(chain: list) -> str | None:
    """Giải thích thay đổi giữa 2 phiên bản gần nhất: diff số liệu (rule-based) +
    tóm tắt nội dung thay đổi (LLM, grounded)."""
    if len(chain) < 2:
        return None
    old, new = chain[-2], chain[-1]
    lines = [f"## Thay đổi: [{old.clause_id}] → [{new.clause_id}]"]

    # Diff số liệu (nếu có)
    if old.metric_value is not None and new.metric_value is not None and old.metric_value != new.metric_value:
        arrow = "tăng" if new.metric_value > old.metric_value else "giảm"
        lines.append(
            f"- Chỉ số: **{_fmt_metric(old)} → {_fmt_metric(new)}** ({arrow})"
        )
    lines.append(f"- Hiệu lực thay đổi từ: **{new.effective_date}**")

    # Giải thích nội dung thay đổi bằng LLM (grounded 2 văn bản)
    if is_configured():
        system = (
            "Bạn so sánh 2 phiên bản của một quy định pháp lý. Tóm tắt NGẮN GỌN "
            "(1-3 câu) ĐIỂM KHÁC NHAU chính, CHỈ dựa trên 2 nội dung được cung cấp, "
            "không bịa. Tiếng Việt."
        )
        prompt = (
            f"PHIÊN BẢN CŨ [{old.clause_id}] (hiệu lực {old.effective_date}):\n{old.text}\n\n"
            f"PHIÊN BẢN MỚI [{new.clause_id}] (hiệu lực {new.effective_date}):\n{new.text}\n\n"
            "Điểm khác nhau chính:"
        )
        try:
            summary = get_llm().generate(system, prompt, timeout=20).strip()
            if summary:
                lines.append(f"\n{summary}")
        except Exception:  # noqa: BLE001 — lỗi LLM → chỉ hiện diff rule-based
            pass
    return "\n".join(lines)
