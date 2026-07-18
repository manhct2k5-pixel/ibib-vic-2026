"""Stage synthesize — dựng prompt từ ứng viên đã annotate và gọi LLM (AD-3).

Chỉ gọi provider LLM (AD-7); không gọi httpx tới Anthropic trực tiếp.
"""

from __future__ import annotations

from pipeline.annotate import CandidateView
from providers.llm import LLMProvider

SYSTEM = (
    "Bạn là trợ lý pháp lý ngân hàng. CHỈ dùng các điều khoản được cung cấp, "
    "không bịa. Trả lời tiếng Việt, ngắn gọn, và luôn trích dẫn clause_id. "
    "Nếu một điều khoản đã bị thay thế, nêu rõ và ưu tiên bản còn hiệu lực."
)


def _format_views(views: list[CandidateView]) -> str:
    lines = []
    for v in views:
        status = "còn hiệu lực"
        if not v.is_current:
            status = "ĐÃ THAY THẾ"
            if v.superseded_by:
                status += f" (bởi {v.superseded_by})"
        lines.append(f"- [{v.clause.clause_id}] ({status}) {v.clause.body}")
    return "\n".join(lines)


def build_prompt(question: str, views: list[CandidateView]) -> str:
    return (
        f"Câu hỏi: {question}\n\n"
        f"Các điều khoản liên quan:\n{_format_views(views)}\n\n"
        "Hãy trả lời câu hỏi dựa trên các điều khoản còn hiệu lực, trích dẫn clause_id."
    )


def synthesize(
    llm: LLMProvider, question: str, views: list[CandidateView]
) -> str:
    return llm.generate(SYSTEM, build_prompt(question, views))
