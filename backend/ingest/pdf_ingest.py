"""Nạp PDF số thành clause phiên (Story 7.6, FR-18/AD-13).

Luồng: PDF → text (pypdf) → cắt theo "Điều N" (regex) → gọi LLM trích
effective_date + tiêu đề → SessionClause (in-memory, KHÔNG persist vào DB global).

Giới hạn (Non-Goal): KHÔNG tự suy quan hệ liên-văn-bản (AMENDS/SUPERSEDES); KHÔNG
OCR (PDF scan). Clause PDF coi là đang hiệu lực tại effective_date trích được.
"""

from __future__ import annotations

import io
import json
import re
from datetime import date

from backend.kb.session_store import SessionClause
from backend.providers.llm import LLMProvider

# Đầu mỗi Điều: "Điều 6." / "Điều 6.3" ở đầu dòng.
_DIEU_RE = re.compile(r"(?m)^\s*Điều\s+(\d+(?:\.\d+)*)\s*\.?\s*")
# Ngày kiểu "ngày 01 tháng 01 năm 2020" hoặc "01/01/2020".
_DATE_TXT_RE = re.compile(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})")
_DATE_SLASH_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
# Chỉ lấy ngày gắn với "hiệu lực" cho chắc.
_EFFECT_RE = re.compile(r"hiệu lực[^.]{0,80}", re.IGNORECASE)

_MAX_LLM_CHARS = 6000


def extract_text(pdf_bytes: bytes) -> str:
    """Trích toàn bộ text từ PDF số (pypdf). PDF scan (ảnh) sẽ ra rỗng."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(parts)


def split_into_clauses(text: str) -> list[dict]:
    """Cắt text thành các Điều theo heading 'Điều N'. Trả [{path, num, text}]."""
    matches = list(_DIEU_RE.finditer(text))
    out: list[dict] = []
    for i, m in enumerate(matches):
        num = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            out.append({"path": f"Điều {num}", "num": num, "text": body})
    return out


def _parse_date_tokens(d: str, mo: str, y: str) -> date | None:
    try:
        return date(int(y), int(mo), int(d))
    except ValueError:
        return None


def _regex_effective_date(text: str) -> date | None:
    """Dự phòng: tìm ngày gần cụm 'hiệu lực'."""
    for seg in _EFFECT_RE.findall(text):
        m = _DATE_TXT_RE.search(seg) or _DATE_SLASH_RE.search(seg)
        if m:
            return _parse_date_tokens(m.group(1), m.group(2), m.group(3))
    return None


def _llm_metadata(llm: LLMProvider, text: str) -> dict:
    """Gọi LLM trích {effective_date, title}. Trả {} nếu lỗi/không rõ."""
    system = (
        "Bạn trích siêu dữ liệu văn bản pháp lý Việt Nam. CHỈ trả JSON, không giải "
        'thích. Khóa: {"effective_date":"YYYY-MM-DD"|null,"title":string|null}. '
        "effective_date là ngày văn bản có HIỆU LỰC (không phải ngày ký nếu khác)."
    )
    prompt = f"Trích effective_date và title từ văn bản sau:\n\n{text[:_MAX_LLM_CHARS]}"
    try:
        raw = llm.generate(system, prompt)
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            return {}
        return json.loads(raw[start : end + 1])
    except (ValueError, KeyError, TypeError):
        return {}


def extract_metadata(llm: LLMProvider, text: str) -> dict:
    """Trích {effective_date, title}. LLM trước, regex dự phòng, cuối cùng hôm nay."""
    meta = _llm_metadata(llm, text)
    eff: date | None = None
    raw_eff = meta.get("effective_date")
    if isinstance(raw_eff, str):
        try:
            eff = date.fromisoformat(raw_eff)
        except ValueError:
            eff = None
    if eff is None:
        eff = _regex_effective_date(text)
    if eff is None:
        eff = date.today()  # fallback: coi như đang hiệu lực
    title = meta.get("title") if isinstance(meta.get("title"), str) else None
    return {"effective_date": eff, "title": title}


def pdf_to_session_clauses(
    pdf_bytes: bytes, doc_code: str, llm: LLMProvider
) -> tuple[list[SessionClause], dict]:
    """PDF → (clause phiên, meta). Clause mang effective_date trích được, public."""
    text = extract_text(pdf_bytes)
    meta = extract_metadata(llm, text)
    eff: date = meta["effective_date"]
    clauses: list[SessionClause] = []
    for seg in split_into_clauses(text):
        clauses.append(
            SessionClause(
                clause_id=f"{doc_code}/{seg['path']}",
                doc_code=doc_code,
                path=seg["path"],
                text=seg["text"],
                effective_date=eff,
                expiry_date=None,  # đang hiệu lực (không suy quan hệ — Non-Goal)
                topic="",
                visibility="public",
                metric_value=None,
                metric_unit=None,
            )
        )
    return clauses, {
        "title": meta.get("title") or doc_code,
        "effective_date": eff.isoformat(),
        "chars": len(text),
    }
