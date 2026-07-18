"""Provider embedding sau interface (AD-7, AD-8) — cho semantic retrieval.

- `EmbeddingProvider` Protocol: `embed_passages(texts)` + `embed_query(text)`.
- `FastEmbedProvider`: chạy LOCAL bằng fastembed (ONNX, không cần torch/mạng khi
  đã tải model). Model `intfloat/multilingual-e5-small` hỗ trợ tiếng Việt.
- `get_embedder()`: trả provider nếu khả dụng; None nếu thiếu lib / tải model lỗi
  / bị tắt bằng env `IBIB_DISABLE_EMBED` (test dùng để giữ kết quả deterministic).

Lý do dùng interface + fallback: nếu không có embedding, repository tự lui về
khớp từ khóa → app/test vẫn chạy, demo không sập khi offline.

**Lưu ý model e5:** phải thêm tiền tố "query: " cho câu hỏi và "passage: " cho
văn bản — nếu không, chất lượng giảm mạnh (yêu cầu của họ model E5).
"""

from __future__ import annotations

import os
from typing import Protocol

DEFAULT_EMBED_MODEL = os.environ.get(
    "EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)


class EmbeddingProvider(Protocol):
    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedProvider:
    """Embedding local qua fastembed. Tải model 1 lần rồi cache trong tiến trình."""

    def __init__(self, model_name: str = DEFAULT_EMBED_MODEL) -> None:
        from fastembed import TextEmbedding  # import trễ: chỉ khi thực sự dùng

        self._model = TextEmbedding(model_name=model_name)
        # Chỉ họ model E5 mới cần tiền tố "query:"/"passage:"; model khác dùng thô.
        self._is_e5 = "e5" in model_name.lower()

    def _p(self, text: str, kind: str) -> str:
        return f"{kind}: {text}" if self._is_e5 else text

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        prefixed = [self._p(t, "passage") for t in texts]
        return [vec.tolist() for vec in self._model.embed(prefixed)]

    def embed_query(self, text: str) -> list[float]:
        vec = next(iter(self._model.embed([self._p(text, "query")])))
        return vec.tolist()


def get_embedder() -> EmbeddingProvider | None:
    # Tắt cứng cho test (giữ retrieval keyword deterministic, không tải model).
    if os.environ.get("IBIB_DISABLE_EMBED") == "1":
        return None
    try:
        return FastEmbedProvider()
    except Exception:  # noqa: BLE001 — thiếu lib/tải model lỗi → lui về keyword
        return None
