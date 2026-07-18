# Backend — Compliance Copilot

FastAPI cung cấp `POST /api/chat`. Story 1.1 = đường ống xanh (trả lời stub từ
`repository` đọc `data/sample/corpus.json`). Pipeline thật đến ở Story 1.2+.

## Chạy

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # điền LLM_API_KEY khi cần (Story 1.5)

uvicorn api.main:app --reload --port 8000
```

- Kiểm tra: `GET http://localhost:8000/health` → `{"status":"ok","clauses":7}`
- Thiếu `data/sample/corpus.json` → app **fail fast** (không khởi động).

## Frontend gọi backend

Trong `frontend/.env.local`:

```env
VITE_API_MODE=real
VITE_API_BASE_URL=http://localhost:8000
```

Đường lui demo: `VITE_API_MODE=mock` (không cần backend).

## Test

```bash
cd backend && source .venv/bin/activate
python -m pytest
```

## Cấu trúc (AD-7 layering: api → pipeline → repository)

```
api/         # FastAPI app, /api/chat, CORS (AD-6, AD-8)
pipeline/    # các stage (Story 1.3-1.5)
kb/          # models.py (Clause), repository.py (AD-12) — stub cho tới Epic 0
providers/   # llm.py (AD-7, AD-8)
db/          # schema.sql, docker-compose.yml (Postgres — Epic 0)
ingest/      # seed_db.py, admin (Epic 0/5)
```

> Truy cập dữ liệu **chỉ** qua `kb/repository.py` (AD-12). Story 1.1 dùng
> `StubRepository`; Epic 0 sẽ thay bằng bản Postgres — giữ nguyên chữ ký hàm.
