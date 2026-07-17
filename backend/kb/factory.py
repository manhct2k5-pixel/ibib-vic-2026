"""Factory tạo Repository — ĐIỂM SWAP DUY NHẤT (AD-12).

Khi Epic 0.4 giao `PostgresRepository`, chỉ đổi thân hàm dưới đây; pipeline/api
không phải sửa gì (cùng Protocol `Repository`).
"""

from __future__ import annotations

import os
from pathlib import Path

from .repository import StubRepository
from .repository_protocol import Repository

# backend/kb/factory.py -> parents[2] = gốc repo
DEFAULT_CORPUS_PATH = str(
    Path(__file__).resolve().parents[2] / "data" / "sample" / "corpus.json"
)


def get_repository(corpus_path: str | None = None) -> Repository:
    corpus_path = corpus_path or os.environ.get("CORPUS_PATH") or DEFAULT_CORPUS_PATH

    # 👉 ĐIỂM SWAP (Epic 0.4): thay dòng dưới bằng
    #    return PostgresRepository(os.environ["DATABASE_URL"])
    return StubRepository.from_corpus(corpus_path)
