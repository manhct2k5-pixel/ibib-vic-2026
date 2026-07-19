import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from backend.kb.kb import KnowledgeBase
from backend.pipeline import pipeline as P

kb = KnowledgeBase.load_from_db()

# Query database directly using engine
from sqlalchemy import text as _sql
from backend.api.database import engine

print("\nQuerying TT39 clauses from database...")
with engine.connect() as conn:
    rows = conn.execute(
        _sql("SELECT clause_id, doc_code, text FROM dwh.dieu_khoan WHERE path = 'Toàn văn'")
    ).all()
    print(f"Total 'Toàn văn' clauses found: {len(rows)}")
    for r in rows:
        print(f"  {r[0]} ({r[1]}): {r[2][:100]}...")

# 3. Check combined and run pipeline
res = P.run_pipeline(q_ood, "2026-07-18", "system", "employee", kb)
print("\nPipeline response:")
print(f"  Answer: {res['answer']}")
print(f"  Confidence: {res['confidence']}")
print(f"  Sources count: {len(res['sources'])}")
print(f"  Living doc count: {len(res['livingDoc']['clauses']) if res.get('livingDoc') else 0}")
