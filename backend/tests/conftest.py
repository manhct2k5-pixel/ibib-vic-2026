"""Cấu hình test dùng chung: KHÔNG bao giờ gọi LLM thật trong test.

`api.main` gọi `load_dotenv()` lúc import nên `LLM_API_KEY` từ `backend/.env`
lọt vào môi trường test → `/api/chat` sẽ gọi API thật (chậm/tốn/flaky). Fixture
autouse dưới đây xóa key trước MỖI test → `get_llm()` luôn trả `MockLLM`.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _force_mock_llm(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
