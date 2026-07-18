"""Stage conflict_check (AD-3) — chạy sau temporal_filter, trước synthesize.

Phát hiện xung đột nằm TRONG repository (`find_conflicts`, AD-12); stage này chỉ
điều phối + lọc theo chủ đề candidate + định dạng thông điệp cảnh báo. Chỉ cảnh
báo các cặp mâu thuẫn có `topic` mà câu trả lời thực sự đụng tới — không làm phiền
người dùng bằng mâu thuẫn ở chủ đề họ không hỏi.
"""

from __future__ import annotations

from datetime import date

from kb.models import Clause
from kb.repository_protocol import Repository


def _fmt(value: float | None, unit: str | None) -> str:
    if value is None:
        return "?"
    num = f"{value:g}"
    return f"{num}{unit}" if unit else num


def check_conflicts(
    repo: Repository,
    candidates: list[Clause],
    as_of: date,
    scope: str = "all",
) -> str | None:
    """Trả chuỗi cảnh báo nếu có xung đột liên quan candidate; None nếu không.

    Xung đột = hai điều khoản cùng `topic`, cùng còn hiệu lực tại `as_of`, khác
    giá trị số (do `repository.find_conflicts` quyết định — quét thật, AD-12).
    """
    topics = {c.topic for c in candidates}
    if not topics:
        return None

    pairs = [p for p in repo.find_conflicts(as_of, scope) if p.topic in topics]
    if not pairs:
        return None

    p = pairs[0]  # cảnh báo cặp đầu tiên liên quan (đủ để người dùng thận trọng)
    return (
        f"Phát hiện xung đột: {p.clause_a.clause_id} ({_fmt(p.value_a, p.unit)}) "
        f"và {p.clause_b.clause_id} ({_fmt(p.value_b, p.unit)}) cùng chủ đề "
        f"'{p.topic}' và cùng còn hiệu lực. Vui lòng kiểm tra trước khi áp dụng."
    )
