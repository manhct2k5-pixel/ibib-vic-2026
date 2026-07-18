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

MANAGER_FORMAT = """
KHUÔN TRẢ LỜI BẮT BUỘC CHO QUẢN LÝ:
## Đối chiếu quy định
### Tầng 1 — Luật ngoài (NHNN)
- **Văn bản:** tên/mã văn bản.
- **Địa chỉ:** Điểm → Khoản → Điều → Tên văn bản.
- **Nội dung:** trích xuất đầy đủ điều khoản tương ứng.
### Tầng 2 — Quy chế nội bộ
- **Văn bản:** tên/mã quy chế nội bộ.
- **Địa chỉ:** Điểm → Khoản → Điều → Tên văn bản.
- **Nội dung:** trích xuất đầy đủ điều khoản tương ứng.
Nếu không tìm thấy một tầng, ghi rõ "Chưa tìm thấy trong nguồn được cung cấp"; không bịa.
## Timeline hiệu lực
Trình bày theo chuỗi: [Văn bản (trạng thái, ngày)] → [Văn bản kế tiếp].
## Phân tích tác động
### Operational Impact — Đối với ngân hàng
Nêu thay đổi quy trình, thẩm quyền phê duyệt, kiểm soát hoặc vận hành.
"""

EMPLOYEE_FORMAT = """
KHUÔN TRẢ LỜI BẮT BUỘC CHO NHÂN VIÊN:
## Ý định người dùng
Tóm tắt ngắn gọn yêu cầu.
## Thực thể và dữ kiện chính
Liệt kê văn bản, điều/khoản/điểm, con số, ngưỡng và nghĩa vụ cần bóc tách.
## Kết luận nghiệp vụ
Trả lời trực tiếp dựa trên điều khoản còn hiệu lực và luôn trích dẫn clause_id.
## Phân tích tác động
### Obligation Impact — Đối với khách hàng
Nêu nghĩa vụ, chứng từ cần bổ sung và thay đổi mà khách hàng phải thực hiện.
## Timeline hiệu lực
Trình bày theo chuỗi: [Văn bản (trạng thái, ngày)] → [Văn bản kế tiếp].
"""


def _format_views(views: list[CandidateView]) -> str:
    lines = []
    for v in views:
        status = "còn hiệu lực"
        if not v.is_current:
            status = "ĐÃ THAY THẾ"
            if v.superseded_by:
                status += f" (bởi {v.superseded_by})"
        layer = "Quy chế nội bộ" if v.clause.visibility == "internal" else "Luật ngoài/NHNN"
        metric = ""
        if v.clause.metric_value is not None:
            metric = f"; metric={v.clause.metric_value} {v.clause.metric_unit or ''}".rstrip()
        expiry = v.clause.expiry_date.isoformat() if v.clause.expiry_date else "chưa xác định"
        lines.append(
            f"- [{v.clause.clause_id}] tầng={layer}; văn bản={v.clause.doc_code}; "
            f"địa chỉ={v.clause.path}; trạng thái={status}; "
            f"hiệu lực={v.clause.effective_date.isoformat()}; hết hiệu lực={expiry}{metric}\n"
            f"  Nội dung: {v.clause.body}"
        )
    return "\n".join(lines)


def build_prompt(
    question: str, views: list[CandidateView], audience: str = "employee"
) -> str:
    response_format = MANAGER_FORMAT if audience == "manager" else EMPLOYEE_FORMAT
    return (
        f"Câu hỏi: {question}\n\n"
        f"Các điều khoản liên quan:\n{_format_views(views)}\n\n"
        "Hãy trả lời câu hỏi dựa trên các điều khoản còn hiệu lực, trích dẫn clause_id.\n\n"
        f"{response_format.strip()}"
    )


def synthesize(
    llm: LLMProvider,
    question: str,
    views: list[CandidateView],
    audience: str = "employee",
) -> str:
    return llm.generate(SYSTEM, build_prompt(question, views, audience))
