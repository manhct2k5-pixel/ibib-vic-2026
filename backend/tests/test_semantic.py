"""Test semantic retrieval (fastembed).

Bật lại embedder (conftest tắt mặc định). Nếu fastembed/model chưa sẵn (offline
CI), skip — retrieval keyword vẫn được các test khác phủ.

Điểm chứng minh: câu hỏi diễn đạt KHÁC từ khóa trong văn bản vẫn tìm đúng clause
— điều mà khớp từ khóa thuần KHÔNG làm được.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

CORPUS = Path(__file__).resolve().parents[2] / "data" / "sample" / "corpus.json"
TODAY = date(2026, 7, 17)


@pytest.fixture()
def semantic_repo(monkeypatch):
    monkeypatch.setenv("IBIB_DISABLE_EMBED", "0")  # bật lại embedder cho test này
    from providers.embeddings import get_embedder

    if get_embedder() is None:
        pytest.skip("fastembed/model chưa sẵn — bỏ qua test semantic")
    from kb.factory import get_repository

    return get_repository(str(CORPUS))


def test_semantic_finds_clause_without_keyword_overlap(semantic_repo) -> None:
    # "vốn đệm an toàn" KHÔNG khớp cụm "tỷ lệ an toàn vốn" theo token thuần,
    # nhưng gần về NGỮ NGHĨA → semantic phải kéo được clause an toàn vốn.
    results = [c.clause_id for c in semantic_repo.search("ngân hàng cần giữ vốn đệm an toàn bao nhiêu", TODAY)]
    assert "TT22/Điều 1" in results  # bản 9% còn hiệu lực


def test_semantic_respects_temporal_and_scope(semantic_repo) -> None:
    # Semantic vẫn phải tôn trọng lọc hiệu lực + visibility (AD-5, AD-11)
    results = semantic_repo.search("tỷ lệ an toàn vốn", TODAY, scope="public")
    ids = {c.clause_id for c in results}
    assert "QD-INT/Điều 2" not in ids  # internal bị loại
    assert "TT41/Điều 6.3" not in ids  # hết hiệu lực bị loại
    assert all(c.visibility == "public" for c in results)
