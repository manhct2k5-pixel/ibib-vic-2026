"""Phân tích văn bản pháp lý upload → metadata + quan hệ liên-văn-bản (FR-17).

MVP dùng DỮ LIỆU TỪ FILE UPLOAD (chưa đụng DB). Mỗi văn bản khai báo quan hệ ngay
trong phần mở đầu ("Căn cứ …" = REFERENCES; "sửa đổi, bổ sung Điều X của Thông tư
số Y" = AMENDS; "thay thế/bãi bỏ" = SUPERSEDES; văn bản hợp nhất = CONSOLIDATES).

`analyze_document` gọi LLM trên ~6000 ký tự đầu (nơi khai báo quan hệ) để trích
JSON, kèm regex dự phòng cho số hiệu + "Căn cứ". Trả metadata + list relation thô;
endpoint sẽ chuẩn hoá doc_code và đối chiếu với các văn bản đã upload.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Optional

from backend.providers.llm import LLMProvider

_MAX_LLM_CHARS = 4000
_LLM_TIMEOUT_S = 45.0  # phân tích sinh JSON dài, cần lâu hơn 15s mặc định


def _normalize_ws(text: str) -> str:
    """Gộp khoảng trắng ngang (PDF hay chèn 2+ space giữa từ), GIỮ newline."""
    return re.sub(r"[^\S\n]+", " ", text or "")

# "Số: 83/2025/TT-NHNN" | "số 39/2016/TT-NHNN" | "21/2021/NĐ-CP" | "20/VBHN-NHNN"
_SOHIEU_RE = re.compile(
    r"[Ss]ố[:\s]+(\d+)\s*/\s*(\d{4})?\s*/?\s*(TT|NĐ|ND|QĐ|QD|VBHN|CT)[-\s]?([A-ZĐ]+)?",
)
_SOHIEU_VBHN_RE = re.compile(r"(\d+)\s*/\s*VBHN[-\s]?([A-ZĐ]+)?")
# Cụm "Căn cứ ... Thông tư/Nghị định/Luật ... số 39/2016"
_CANCU_RE = re.compile(
    r"Căn cứ[^;.\n]{0,160}?(?:Thông tư|Nghị định|Luật|Quyết định)[^;.\n]{0,80}?"
    r"số\s+(\d+)\s*/\s*(\d{4})",
    re.IGNORECASE,
)
# Cụm "sửa đổi, bổ sung ... Thông tư số 39/2016"
_SUADOI_RE = re.compile(
    r"(sửa đổi|bổ sung|thay thế|bãi bỏ)[^.\n]{0,120}?"
    r"(?:Thông tư|Nghị định|Quyết định)[^.\n]{0,40}?số\s+(\d+)\s*/\s*(\d{4})",
    re.IGNORECASE,
)

_TYPE_PREFIX = {
    "TT": "TT", "THÔNG TƯ": "TT",
    "NĐ": "ND", "ND": "ND", "NGHỊ ĐỊNH": "ND",
    "QĐ": "QD", "QD": "QD", "QUYẾT ĐỊNH": "QD",
    "VBHN": "VBHN",
    "CT": "CT", "CHỈ THỊ": "CT",
    "LUẬT": "LUAT",
}


def normalize_doc_code(raw: str) -> str:
    """Chuẩn hoá tham chiếu văn bản → mã ngắn ổn định: TT39, ND21, VBHN20, QD1627.

    Bắt số hiệu đầu tiên + loại. Không nhận dạng được → trả chuỗi rút gọn của raw.
    """
    if not raw:
        return ""
    s = raw.strip()
    # VBHN: "20/VBHN-NHNN"
    m = _SOHIEU_VBHN_RE.search(s)
    if m:
        return f"VBHN{m.group(1)}"
    # Dạng "số 39/2016/TT-NHNN" hoặc "39/2016/TT-NHNN"
    m = re.search(r"(\d+)\s*/\s*(\d{4})\s*/\s*(TT|NĐ|ND|QĐ|QD|VBHN|CT)", s)
    if m:
        prefix = _TYPE_PREFIX.get(m.group(3).upper(), m.group(3).upper())
        return f"{prefix}{m.group(1)}"
    # Luật/Bộ luật theo số Quốc hội: "số 46/2010/QH12" → Luat46
    m = re.search(r"(\d+)\s*/\s*(\d{4})\s*/\s*QH", s)
    if m:
        return f"Luat{m.group(1)}"
    # Dạng chữ: "Thông tư số 39/2016"
    m = re.search(
        r"(Thông tư|Nghị định|Quyết định|Chỉ thị|Luật)[^\d]{0,20}?(\d+)\s*/\s*(\d{4})",
        s, re.IGNORECASE,
    )
    if m:
        prefix = _TYPE_PREFIX.get(m.group(1).upper(), "VB")
        return f"{prefix}{m.group(2)}"
    # Chỉ có "số 39/2016"
    m = re.search(r"(\d+)\s*/\s*(\d{4})", s)
    if m:
        return f"VB{m.group(1)}-{m.group(2)}"
    # Luật/Bộ luật nêu theo tên (không số): rút gọn tên sạch để làm nhãn node
    m = re.search(r"(Bộ luật|Luật)\s+([A-ZÀ-Ỹ][^;.\n]{0,30})", s)
    if m:
        return f"{m.group(1)} {m.group(2)}".strip()[:28]
    return re.sub(r"\s+", " ", s).strip()[:28]


def _parse_iso(v: object) -> Optional[date]:
    if isinstance(v, str):
        try:
            return date.fromisoformat(v[:10])
        except ValueError:
            return None
    return None


_HEADER_DATE_RE = re.compile(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})")


def _regex_header_date(text: str) -> Optional[date]:
    """Ngày ở header (thường là ngày ban hành) — dự phòng khi LLM không trả date."""
    m = _HEADER_DATE_RE.search(text[:600])
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


def _llm_analyze(llm: LLMProvider, text: str) -> dict:
    system = (
        "Bạn phân tích văn bản pháp lý Việt Nam. CHỈ trả JSON, không giải thích. "
        "Khóa bắt buộc: doc_code (số hiệu NGẮN gọn ví dụ 'TT39','ND21','VBHN20'), "
        "title (tên văn bản), doc_type (Thông tư|Nghị định|Quyết định|VBHN|Luật), "
        "issuer (cơ quan ban hành), effective_date (YYYY-MM-DD hoặc null), "
        "relations (mảng). Mỗi relation là quan hệ mà VĂN BẢN NÀY tuyên bố với văn "
        "bản khác: {type, target_doc, target_article, note}. type ∈ "
        "{AMENDS(sửa đổi/bổ sung điều khoản của văn bản khác), "
        "SUPERSEDES(thay thế/bãi bỏ văn bản khác), "
        "REFERENCES(căn cứ/dẫn chiếu), CONSOLIDATES, GUIDES(hướng dẫn thi hành)}. "
        "QUAN TRỌNG: nếu đây là VĂN BẢN HỢP NHẤT (VBHN), hãy dùng type=CONSOLIDATES "
        "liệt kê TẤT CẢ văn bản GỐC và các văn bản SỬA ĐỔI được hợp nhất trong đó "
        "(thường nêu ở phần đầu/chú thích). target_doc là số hiệu văn bản đích; "
        "target_article là 'Điều N' nếu nêu rõ, không thì null; note mô tả ngắn."
    )
    prompt = f"Phân tích văn bản sau và trả JSON:\n\n{text[:_MAX_LLM_CHARS]}"
    try:
        raw = llm.generate(system, prompt, timeout=_LLM_TIMEOUT_S)
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            return {}
        return json.loads(raw[start : end + 1])
    except Exception:  # noqa: BLE001 — LLM lỗi/timeout → rơi về regex, không sập demo
        return {}


def _doc_code_from_filename(filename: str) -> str:
    """Suy mã văn bản từ TÊN FILE (đáng tin hơn OCR header). '' nếu không rõ.

    Xử lý: 'VanBanGoc_Thông tư 39-2016-TT-NHNN', '41.2016.TT.NHNN', 'TT 13-2018',
    '20_VBHN-NHNN', '21_2021_ND-CP', '83_2025_TT-NHNN'.
    """
    base = re.sub(r"\.(pdf|docx?)$", "", filename or "", flags=re.IGNORECASE)
    base = re.sub(r"(?i)^vanbangoc[_\s-]*", "", base)
    up = base.upper()
    # VBHN: "20_VBHN" / "VBHN-20"
    m = re.search(r"(\d+)[\s_.\-]*VBHN", up) or re.search(r"VBHN[\s_.\-]*(\d+)", up)
    if m:
        return f"VBHN{m.group(1)}"
    # Loại chữ đứng trước số: "THÔNG TƯ 39", "NGHỊ ĐỊNH 21", "QUYẾT ĐỊNH 1627"
    for word, pre in (("THÔNG TƯ", "TT"), ("NGHỊ ĐỊNH", "ND"),
                      ("QUYẾT ĐỊNH", "QD"), ("CHỈ THỊ", "CT")):
        m = re.search(word + r"\s*(\d+)", up)
        if m:
            return f"{pre}{m.group(1)}"
    # Dạng số-năm-loại: "39-2016-TT", "41.2016.TT", "83_2025_TT", "13-2018-TT"
    m = re.search(r"(\d+)[.\-_/](\d{4})[.\-_/\s]*(TT|NĐ|ND|QĐ|QD|CT)", up)
    if m:
        return f"{_TYPE_PREFIX.get(m.group(3), m.group(3))}{m.group(1)}"
    # Dạng "TT 13", "ND 21" (loại viết tắt đứng trước số)
    m = re.search(r"\b(TT|NĐ|ND|QĐ|QD|CT)\s*[.\-_]?\s*(\d+)", up)
    if m:
        return f"{_TYPE_PREFIX.get(m.group(1), m.group(1))}{m.group(2)}"
    return ""


def doc_code_from_filename(filename: str) -> str:
    """Mã văn bản suy từ TÊN FILE (không cần đọc nội dung → không OCR). Trả
    'TAILIEU' nếu không nhận dạng được. Dùng để trả docCode ngay khi upload nền."""
    return _doc_code_from_filename(filename) or "TAILIEU"


def _regex_doc_code(text: str, filename: str) -> str:
    # Ưu tiên tên file (ổn định hơn text OCR nhiễu)
    fn = _doc_code_from_filename(filename)
    if fn:
        return fn
    m = _SOHIEU_VBHN_RE.search(text[:800])
    if m:
        return f"VBHN{m.group(1)}"
    m = _SOHIEU_RE.search(text[:800])
    if m:
        prefix = _TYPE_PREFIX.get((m.group(3) or "").upper(), (m.group(3) or "VB"))
        return f"{prefix}{m.group(1)}"
    base = re.sub(r"\.(pdf|docx?)$", "", filename or "", flags=re.IGNORECASE)
    return base[:16] or "TAILIEU"


def _regex_relations(text: str) -> list[dict]:
    """Dự phòng: trích REFERENCES từ 'Căn cứ' + AMENDS/SUPERSEDES từ 'sửa đổi …'."""
    out: list[dict] = []
    head = text[:_MAX_LLM_CHARS]
    for m in _CANCU_RE.finditer(head):
        out.append({
            "type": "REFERENCES",
            "target_doc": f"{m.group(1)}/{m.group(2)}",
            "target_article": None,
            "note": "Căn cứ pháp lý",
        })
    for m in _SUADOI_RE.finditer(head):
        verb = m.group(1).lower()
        rtype = "SUPERSEDES" if verb in ("thay thế", "bãi bỏ") else "AMENDS"
        out.append({
            "type": rtype,
            "target_doc": f"{m.group(2)}/{m.group(3)}",
            "target_article": None,
            "note": f"{verb.capitalize()} văn bản",
        })
    return out


def quick_metadata(text: str, filename: str) -> dict:
    """Metadata NHANH chỉ bằng regex (KHÔNG gọi LLM) — dùng lúc upload.

    Trả {doc_code, effective_date(date|None), head} với head là ~4000 ký tự đầu đã
    chuẩn hoá khoảng trắng (để phân tích LLM trễ lúc gửi chat).
    """
    norm = _normalize_ws(text)
    return {
        "doc_code": _regex_doc_code(text, filename),
        "effective_date": _regex_header_date(norm),
        "head": norm[:_MAX_LLM_CHARS],
    }


def analyze_document(text: str, filename: str, llm: LLMProvider) -> dict:
    """Trả {doc_code, title, doc_type, issuer, effective_date(date|None), relations[]}.

    LLM trước; regex bù số hiệu + quan hệ (căn cứ/sửa đổi) nếu LLM thiếu.
    relations[].target_doc đã chuẩn hoá về mã ngắn.
    """
    text = _normalize_ws(text)
    meta = _llm_analyze(llm, text)

    doc_code = str(meta.get("doc_code") or "").strip()
    if not doc_code or len(doc_code) > 16:
        doc_code = _regex_doc_code(text, filename)
    else:
        doc_code = normalize_doc_code(doc_code)

    relations: list[dict] = []
    seen: set = set()

    def _add(r: dict) -> None:
        tgt = normalize_doc_code(str(r.get("target_doc") or ""))
        if not tgt or tgt == doc_code:
            return
        rtype = str(r.get("type") or "REFERENCES").upper()
        key = (rtype, tgt, r.get("target_article") or "")
        if key in seen:
            return
        seen.add(key)
        relations.append({
            "type": rtype,
            "target_doc": tgt,
            "target_article": (str(r["target_article"]) if r.get("target_article") else None),
            "note": (str(r["note"]) if r.get("note") else None),
        })

    if isinstance(meta.get("relations"), list):
        for r in meta["relations"]:
            if isinstance(r, dict):
                _add(r)
    for r in _regex_relations(text):  # bù các quan hệ LLM có thể bỏ sót
        _add(r)

    eff = _parse_iso(meta.get("effective_date")) or _regex_header_date(text)
    return {
        "doc_code": doc_code,
        "title": str(meta.get("title") or "").strip() or doc_code,
        "doc_type": str(meta.get("doc_type") or "").strip(),
        "issuer": str(meta.get("issuer") or "").strip(),
        "effective_date": eff,
        "relations": relations,
    }
