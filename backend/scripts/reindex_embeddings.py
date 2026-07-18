"""Re-index embedding ngữ nghĩa cho corpus (dwh.anh_xa).

Đổi chiều cột sang EMBED_DIM (e5-large=1024), tính embedding THẬT (API) cho mọi
điều khoản trong dwh.dieu_khoan và ghi lại. Chạy 1 lần (và mỗi khi đổi model).

Cách chạy (từ gốc repo):
    ./backend/.venv/bin/python backend/scripts/reindex_embeddings.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from sqlmodel import Session, select
from sqlalchemy import text

from backend.api.database import engine
from backend.api.models import Clause, ClauseEmbedding
from backend.kb.vector_helper import EMBED_DIM, EMBED_MODEL, embed_passages, embed_available

BATCH = 32


def main() -> None:
    if not embed_available():
        print("THIẾU LLM_API_KEY/LLM_BASE_URL → không thể tính embedding. Dừng.")
        return
    print(f"Model: {EMBED_MODEL} | dim: {EMBED_DIM}")

    # 1. Dọn dữ liệu cũ + đổi chiều cột (data cũ là embedding giả)
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM dwh.anh_xa"))
        conn.execute(
            text(f"ALTER TABLE dwh.anh_xa ALTER COLUMN embedding TYPE vector({EMBED_DIM})")
        )
        conn.commit()
    print("Đã dọn + đổi chiều cột anh_xa.")

    # 2. Tính embedding thật theo lô + ghi
    with Session(engine) as s:
        clauses = s.exec(select(Clause)).all()
        print(f"Tổng điều khoản: {len(clauses)}")
        done = 0
        for i in range(0, len(clauses), BATCH):
            batch = clauses[i : i + BATCH]
            vecs = embed_passages([c.text for c in batch])
            for c, v in zip(batch, vecs):
                s.add(ClauseEmbedding(clause_id=c.clause_id, embedding=v))
            s.commit()
            done += len(batch)
            print(f"  indexed {done}/{len(clauses)}")
    print("XONG.")


if __name__ == "__main__":
    main()
