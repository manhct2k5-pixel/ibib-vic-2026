"""Kiểm thử nhanh #1 (LLM synthesize) + #2 (hybrid semantic search).

Chạy từ gốc repo (cần backend/.env có LLM_API_KEY + DATABASE_URL):
    ./backend/.venv/bin/python backend/verify_features.py
"""

import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from backend.kb.kb import KnowledgeBase
from backend.pipeline import pipeline as P


def line(t=""):
    print(t)


kb = KnowledgeBase.load_from_db()
line("=" * 70)

# ── #2: HYBRID SEMANTIC — câu hỏi DIỄN GIẢI, không trùng từ khóa với điều khoản ──
q2 = "ngân hàng cần giữ bao nhiêu vốn để phòng ngừa rủi ro"
line(f"[#2] Câu hỏi diễn giải (không có từ 'CAR'/'an toàn vốn'):\n  {q2}")
bm = P.retrieve_stage(q2, kb, "employee", None)
vec = P.vector_retrieve_stage(q2, kb, "employee", None)
line(f"  BM25 (từ khóa) tìm được : {[c.clause_id for c in bm[:5]]}")
line(f"  VECTOR (ngữ nghĩa) tìm  : {[c.clause_id for c in vec[:5]]}")
line("  → Nếu BM25 KHÔNG có TT22/Điều 1 mà VECTOR CÓ → semantic search phát huy.")
line("-" * 70)

# ── #1: LLM SYNTHESIZE — system mode (LLM) vs baseline mode (liệt kê thô) ──
q1 = "tỷ lệ an toàn vốn tối thiểu hiện nay là bao nhiêu"
line(f"[#1] Câu hỏi: {q1}")
t = time.time()
sys_r = P.run_pipeline(q1, "2026-07-18", "system", "employee", kb)
line(f"\n  >>> SYSTEM MODE (LLM synthesize, {time.time()-t:.1f}s):")
line("  " + sys_r["answer"].replace("\n", "\n  "))
base_r = P.run_pipeline(q1, "2026-07-18", "baseline", "employee", kb)
line("\n  >>> BASELINE MODE (RAG thường, liệt kê thô — để so sánh):")
line("  " + base_r["answer"][:300].replace("\n", "\n  ") + " …")
line("-" * 70)
line(f"Nguồn (system): {[s['clause_id'] for s in sys_r['sources'][:6]]}")
line(f"Cảnh báo xung đột: {bool(sys_r.get('conflictWarning'))}")
line("=" * 70)
line("XONG. #1 = câu trả lời gọn có [trích nguồn]; #2 = vector tìm đúng theo nghĩa.")
