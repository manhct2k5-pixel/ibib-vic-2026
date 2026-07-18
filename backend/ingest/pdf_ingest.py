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


import os

# Cấu hình OCR qua ENV (quan trọng khi deploy máy chủ yếu — Render free 0.5CPU/512MB):
#   OCR_MAX_PAGES: trần số trang OCR (mặc định 40)
#   OCR_SCALE: độ phân giải render (2.0 nét; 1.5 nhẹ RAM/CPU hơn)
#   OCR_WORKERS: số luồng OCR song song. Máy YẾU nên đặt 1 (tránh OOM); máy nhiều
#                core đặt 2-4 để nhanh. Mặc định co theo số CPU.
_OCR_MAX_PAGES = int(os.environ.get("OCR_MAX_PAGES", "40"))
_OCR_SCALE = float(os.environ.get("OCR_SCALE", "2.0"))
_OCR_WORKERS = int(
    os.environ.get("OCR_WORKERS", str(max(1, min(4, (os.cpu_count() or 2)))))
)


def _extract_text_native(pdf_bytes: bytes) -> str:
    """Trích text từ lớp text của PDF (pypdf). PDF scan/font hỏng sẽ ra rỗng/mojibake."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(parts)


def _ocr_one_page(args) -> tuple[int, str]:
    i, img = args
    import pytesseract

    try:
        return i, pytesseract.image_to_string(img, lang="vie")
    except Exception:  # noqa: BLE001 — 1 trang lỗi không chặn cả file
        return i, ""


def _ocr_pdf(pdf_bytes: bytes) -> str:
    """OCR tiếng Việt: render trang → ảnh → tesseract (lang=vie).

    Xử lý theo LÔ (mỗi lô = số luồng) để chặn RAM: chỉ giữ tối đa `_OCR_WORKERS`
    ảnh trong bộ nhớ cùng lúc → tránh OOM trên máy chủ 512MB (Render free). OCR
    song song trong lô (tesseract chạy tiến trình riêng). Thiếu lib/lỗi → trả ''.
    """
    try:
        import pypdfium2 as pdfium
        import pytesseract  # noqa: F401 — kiểm tra có sẵn
    except ImportError:
        return ""
    try:
        pdf = pdfium.PdfDocument(pdf_bytes)
    except Exception:  # noqa: BLE001 — PDF hỏng
        return ""
    from concurrent.futures import ThreadPoolExecutor

    n = min(len(pdf), _OCR_MAX_PAGES)
    results: dict[int, str] = {}
    with ThreadPoolExecutor(max_workers=_OCR_WORKERS) as ex:
        for start in range(0, n, _OCR_WORKERS):
            # Render 1 lô (pdfium render không thread-safe → render tuần tự)
            batch = []
            for i in range(start, min(start + _OCR_WORKERS, n)):
                try:
                    batch.append((i, pdf[i].render(scale=_OCR_SCALE).to_pil()))
                except Exception:  # noqa: BLE001
                    continue
            # OCR cả lô song song, rồi giải phóng ảnh (batch ra khỏi scope)
            for i, txt in ex.map(_ocr_one_page, batch):
                results[i] = txt
    return "\n".join(results[i] for i in sorted(results))


def extract_text(pdf_bytes: bytes) -> str:
    """Trích text PDF. Ưu tiên lớp text (nhanh); nếu không có cấu trúc 'Điều'
    (scan/font hỏng) thì fallback OCR tiếng Việt."""
    native = _extract_text_native(pdf_bytes)
    if "Điều" in native or "ĐIỀU" in native:
        return native
    ocr = _ocr_pdf(pdf_bytes)
    # OCR ra được 'Điều' → dùng OCR; nếu không, trả bản tốt hơn (dài hơn)
    if "Điều" in ocr or len(ocr) > len(native):
        return ocr
    return native


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


def clauses_from_text(text: str, doc_code: str, eff: date) -> list[SessionClause]:
    """Cắt Điều từ text đã trích sẵn → SessionClause (dùng doc_code cho trước)."""
    clauses: list[SessionClause] = []
    for seg in split_into_clauses(text):
        clauses.append(
            SessionClause(
                clause_id=f"{doc_code}/{seg['path']}",
                doc_code=doc_code,
                path=seg["path"],
                text=seg["text"],
                effective_date=eff,
                expiry_date=None,
                topic="",
                visibility="public",
                metric_value=None,
                metric_unit=None,
            )
        )
    return clauses


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
