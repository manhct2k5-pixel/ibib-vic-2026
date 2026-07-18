"""Embedding ngữ nghĩa qua API (OpenAI-compat, mặc định FPT multilingual-e5-large).

- API-based → chạy được trên máy chủ yếu (Render free) mà KHÔNG cần model local.
- Model họ E5 yêu cầu tiền tố "query: " cho câu hỏi và "passage: " cho văn bản.
- Có fallback: lỗi/thiếu cấu hình → trả vector 0 (retrieve tự lui về BM25).

Dùng chung LLM_API_KEY / LLM_BASE_URL với provider LLM (cùng cổng FPT).
"""

from __future__ import annotations

import os
from typing import List, Optional

import httpx

EMBED_MODEL = os.environ.get("EMBED_MODEL", "multilingual-e5-large")
EMBED_DIM = int(os.environ.get("EMBED_DIM", "1024"))  # e5-large = 1024
_TIMEOUT_S = 30.0


def _base_url() -> str:
    return os.environ.get("LLM_BASE_URL", "").rstrip("/")


def _key() -> str:
    return os.environ.get("LLM_API_KEY", "")


def embed_available() -> bool:
    """Có đủ cấu hình để gọi embedding API không."""
    return bool(_key() and _base_url())


def _embed(inputs: List[str]) -> List[List[float]]:
    """Gọi API embeddings (batch). Giữ đúng thứ tự theo 'index'."""
    resp = httpx.post(
        f"{_base_url()}/embeddings",
        headers={"Authorization": f"Bearer {_key()}", "content-type": "application/json"},
        json={"model": EMBED_MODEL, "input": inputs},
        timeout=_TIMEOUT_S,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    data.sort(key=lambda d: d.get("index", 0))
    return [d["embedding"] for d in data]


def embed_passages(texts: List[str]) -> List[List[float]]:
    """Embedding cho VĂN BẢN (thêm tiền tố 'passage: ' theo yêu cầu model E5)."""
    return _embed([f"passage: {t}" for t in texts])


def embed_query(text: str) -> Optional[List[float]]:
    """Embedding cho CÂU HỎI ('query: '). Trả None nếu lỗi/thiếu cấu hình."""
    if not embed_available():
        return None
    try:
        return _embed([f"query: {text}"])[0]
    except Exception:  # noqa: BLE001 — lỗi API → caller lui về BM25
        return None


def get_text_embedding(text: str) -> List[float]:
    """Embedding THẬT cho 1 văn bản (dùng khi seed/approve admin ghi vào anh_xa).

    Lỗi/thiếu cấu hình → vector 0 (không làm sập luồng approve; clause vẫn lưu, chỉ
    là không tìm được bằng vector cho tới khi re-index)."""
    if not text or not embed_available():
        return [0.0] * EMBED_DIM
    try:
        return embed_passages([text])[0]
    except Exception:  # noqa: BLE001
        return [0.0] * EMBED_DIM
