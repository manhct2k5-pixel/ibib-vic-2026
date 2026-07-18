---
baseline_commit: f12c67d723f79a905aad1904d0d41343906bb622
---

# Story 1.1: Đường ống xanh (skeleton + contract + corpus)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a lập trình viên trong đội IBIB,
I want một đường ống end-to-end (Frontend → `POST /api/chat` → Backend trả lời stub) cùng corpus schema và API contract đã khóa,
so that cả 2–3 người có mặt bằng chung, chạy được, để làm song song ngay từ giờ H0.

## Acceptance Criteria

1. **Skeleton backend + endpoint đúng contract.** Có `backend/` với cây thư mục `api/pipeline/kb/providers/ingest`; chạy `uvicorn` lên được; `POST /api/chat` nhận `{question, asOf?, mode?}` và trả `{answer, sources[], conflictWarning?}` đúng `docs/architecture/API_CONTRACT.md`; có header CORS cho `http://localhost:5173`; lỗi trả HTTP đúng + trường `detail`. (AD-3 khung, AD-6)
2. **Frontend gọi thật được.** Ở `VITE_API_MODE=real`, frontend gọi backend và hiển thị câu trả lời (stub) + nguồn. `chatApi.ts` được cập nhật để `SourceItem` có `clause_id` và (tùy chọn) gửi `asOf`/`mode`. (AD-6)
3. **Dữ liệu qua Repository stub.** Story này KHÔNG tự nạp corpus (dữ liệu là **Epic 0 — Database**). Endpoint lấy nguồn từ một **`repository` stub** (dữ liệu cứng, đúng chữ ký hàm của Story 0.4) để đường ống xanh chạy độc lập; khi Epic 0.4 xong sẽ thay stub bằng repository Postgres thật, KHÔNG đổi chữ ký. (Ranh giới bàn giao Epic 0)
4. **Bảo mật nền.** Key LLM đọc từ `.env` backend (chưa dùng ở story này cũng phải nạp được); **không** có key nào ở frontend; frontend chỉ gọi `/api/*`. (AD-8)
5. **Chạy được đồng thời.** Tài liệu/lệnh chạy 3 tiến trình cục bộ (FE:5173, BE:8000) rõ ràng; `VITE_API_MODE=mock` vẫn hoạt động như đường lui. (DEPLOY, NFR-3)

## Tasks / Subtasks

- [x]**Task 1 — Dựng skeleton FastAPI** (AC: 1, 3, 4)
  - [x]Tạo `backend/` với cây: `api/` `pipeline/` `kb/` `providers/` `ingest/` + `requirements.txt` + `.env.example` (đã có ở root — sao chép/trỏ đúng)
  - [x]`api/main.py`: khởi tạo FastAPI, bật CORS cho `http://localhost:5173`, mount route `/api/chat`
  - [x]`kb/knowledgebase.py`: hàm `load_corpus(path)` đọc `data/sample/corpus.json`; nếu thiếu file → raise + log rõ, chặn startup (fail fast). Lưu vào biến `current_kb` (story này chỉ cần giữ dữ liệu thô + đếm clause; đồ thị/BM25 để Story 1.2)
  - [x]Nạp corpus ở sự kiện startup của app
  - [x]Đọc `LLM_API_KEY` từ env qua `providers/llm.py` (chưa gọi LLM; chỉ xác nhận nạp được, không log giá trị)
- [x]**Task 2 — Endpoint `/api/chat` đúng contract** (AC: 1)
  - [x]Pydantic `ChatRequest {question: str, asOf: str | None, mode: str | None}` và `ChatResponse {answer: str, sources: list[Source], conflictWarning: str | None}` với `Source {clause_id, name, description}`
  - [x]Trả lời **stub** (chưa có pipeline thật): `answer` echo câu hỏi + ghi chú "đường ống xanh", `sources` gồm 1 phần tử lấy từ 1 clause bất kỳ trong corpus (để chứng minh đã nạp được data) — có `clause_id` thật
  - [x]Xử lý lỗi → HTTP 400/422/500 + `{detail}` (đúng `API_CONTRACT.md`)
- [x]**Task 3 — Cập nhật frontend gọi thật** (AC: 2, 5)
  - [x]UPDATE `frontend/src/services/chatApi.ts`: `SourceItem` thêm `clause_id: string`; `ChatResponse` thêm `conflictWarning?: string | null`; `parseSources` đọc `clause_id`; body request gửi kèm `asOf`/`mode` khi có (giữ tương thích: mock vẫn chạy)
  - [x]UPDATE mock response trong `chatApi.ts` để có `clause_id` (đồng bộ shape với real)
  - [x]Xác nhận `VITE_API_MODE=real` + `VITE_API_BASE_URL=http://localhost:8000` gọi được backend và render câu trả lời + nguồn
- [x]**Task 4 — Chạy được & tài liệu** (AC: 5)
  - [x]Thêm lệnh chạy backend vào README/backend (`uvicorn api.main:app --reload --port 8000`)
  - [x]Kiểm thử thủ công: bật BE → bật FE (`npm run dev`) → gửi câu hỏi → thấy trả lời stub + nguồn có `clause_id`
  - [x]Kiểm `mock` mode vẫn hoạt động (đường lui demo)
- [x]**Task 5 — Test tối thiểu** (AC: 1, 3)
  - [x]Test: startup thiếu `corpus.json` → fail fast (không im lặng chạy tiếp)
  - [x]Test: `POST /api/chat` với `{question}` → 200 + response có `answer` (str) và `sources[].clause_id`

## Dev Notes

### Phạm vi story này (đọc kỹ để KHÔNG làm quá)
Đây **chỉ là đường ống xanh**: cấu trúc + hợp đồng + nạp corpus + trả lời **stub**. **KHÔNG** làm retrieve/temporal/LLM thật ở đây — những cái đó là Story 1.2→1.5. Mục tiêu: cuối story, gõ câu hỏi ở FE (real mode) ra được một câu trả lời giả có `clause_id` thật từ corpus. Đó là mặt bằng để mọi người bổ vào song song.

### Tài sản ĐÃ CÓ (đừng tạo lại)
- ✅ `data/sample/corpus.schema.json` và `data/sample/corpus.json` **đã tồn tại** (7 clause, 3 văn bản, validate OK). Story này chỉ **nạp** chúng, không viết lại. [Source: data/sample/corpus.json]
- ✅ Frontend React+TS+Vite đã có, kèm `src/services/chatApi.ts` (cần **UPDATE**, không viết mới). [Source: frontend/src/services/chatApi.ts]
- ✅ `.env.example` root có `LLM_API_KEY`, `LLM_BACKUP_API_KEY`, `BACKEND_URL`. [Source: .env.example]
- ✅ `frontend/.env.example` có `VITE_API_MODE`, `VITE_API_BASE_URL`. [Source: frontend/.env.example]

### File sẽ chạm
| File | NEW/UPDATE | Ghi chú |
|---|---|---|
| `backend/api/main.py` | NEW | FastAPI app, CORS, route |
| `backend/api/chat.py` (hoặc trong main) | NEW | endpoint `/api/chat` |
| `backend/kb/knowledgebase.py` | NEW | `load_corpus` + `current_kb` |
| `backend/providers/llm.py` | NEW | nạp key (chưa gọi) |
| `backend/pipeline/`, `backend/ingest/` | NEW (rỗng/placeholder) | giữ chỗ cho story sau |
| `backend/requirements.txt` | NEW | pin version dưới |
| `frontend/src/services/chatApi.ts` | **UPDATE** | thêm `clause_id`, `conflictWarning`, gửi `asOf`/`mode` |

### Guardrail kiến trúc (BẮT BUỘC theo)
- **Hướng phụ thuộc:** `api → pipeline → kb`; tầng dưới không import tầng trên. LLM sau `providers/llm.py` (interface). [Source: ARCHITECTURE-SPINE.md#AD-7]
- **Contract đóng băng:** request `{question, asOf?, mode?}`, `sources[]={clause_id,name,description}`, lỗi `{detail}`. [Source: ARCHITECTURE-SPINE.md#AD-6, docs/architecture/API_CONTRACT.md]
- **Corpus = nguồn sự thật duy nhất**, `edges.from/to = clause_id`, nạp 1 lần (bất biến). Reload/atomic-swap là chuyện Story 5.1 — story này chỉ nạp lúc startup. [Source: ARCHITECTURE-SPINE.md#AD-1, #AD-2]
- **Secret chỉ ở backend**, không lộ FE. [Source: ARCHITECTURE-SPINE.md#AD-8]
- **KHÔNG dùng embedding/vector DB** (MVP BM25-only) — story này còn chưa cần cả BM25. [Source: ARCHITECTURE-SPINE.md#AD-7, Deferred]

### Tech stack (pin — đã tra web 7/2026)
- Python **3.12**; FastAPI **0.139.2**; uvicorn (mới nhất); pydantic v2. httpx **0.28.1** (để sẵn cho story LLM). [Source: ARCHITECTURE-SPINE.md#Stack]
- Frontend đã pin: React 19 / TypeScript ~6 / Vite 8. Không nâng/hạ. [Source: frontend/package.json]
- `requirements.txt` tối thiểu cho story này: `fastapi==0.139.2`, `uvicorn[standard]`, `pydantic>=2`.

### Cảnh báo regression (đọc file trước khi sửa)
`chatApi.ts` hiện: chỉ gửi `{question}`; `SourceItem` chưa có `clause_id`; có sẵn xử lý timeout 15s + lỗi CORS/JSON rất tốt — **giữ nguyên phần xử lý lỗi/timeout đó**, chỉ mở rộng type + body. Đừng viết lại cả file. [Source: frontend/src/services/chatApi.ts]

### Deployment / chạy
- Backend: `cd backend && uvicorn api.main:app --reload --port 8000` (đọc `.env` cùng chỗ).
- Frontend: `cd frontend && npm run dev` (cổng 5173). Đặt `frontend/.env.local`: `VITE_API_MODE=real`.
- Fail fast: thiếu `data/sample/corpus.json` → backend thoát với log; không chạy tiếp câm lặng. [Source: ARCHITECTURE-SPINE.md#Deployment]

### Testing standards
- Backend: pytest + FastAPI `TestClient`. Tối thiểu 2 test ở Task 5. Đặt trong `backend/tests/` hoặc `tests/` root.
- Không cần coverage cao ở story hạ tầng này; ưu tiên 2 test chặn (fail-fast + contract shape).

### Project Structure Notes
- Cây `backend/` khớp Source Tree trong spine (`api/pipeline/kb/providers/ingest`). [Source: ARCHITECTURE-SPINE.md#Structural Seed]
- `data/sample/` nằm ở root repo (không trong backend) — backend trỏ đường dẫn tương đối `../data/sample/corpus.json` hoặc qua biến env `CORPUS_PATH`. Ghi rõ lựa chọn để story sau (5.1) dùng lại.
- Không mâu thuẫn cấu trúc phát hiện được.

### References
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-ibib-vic-2026-2026-07-17/ARCHITECTURE-SPINE.md#AD-1,AD-2,AD-3,AD-6,AD-7,AD-8]
- [Source: docs/architecture/API_CONTRACT.md]
- [Source: frontend/src/services/chatApi.ts]
- [Source: data/sample/corpus.json, data/sample/corpus.schema.json]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (cc/claude-opus-4-8) — bmad-dev-story

### Debug Log References

- `pytest` (backend): **3 passed** (contract shape, asOf/mode, fail-fast thiếu corpus).
- `tsc -b` (frontend): exit 0 — không lỗi type sau khi thêm `clauseId`/`conflictWarning`.
- `oxlint src/services/chatApi.ts`: exit 0.

### Completion Notes List

- Dựng skeleton FastAPI đúng cây `api/pipeline/kb/providers/ingest` + `db/` (Postgres của Epic 0 để sẵn).
- `POST /api/chat` trả lời **stub** đúng contract (AD-6): request `{question, asOf?, mode?}` → `{answer, sources[{clause_id,name,description}], conflictWarning}`. CORS cho `http://localhost:5173`.
- **Repository stub** (`kb/repository.py`) đọc `data/sample/corpus.json` lúc startup, **fail fast** nếu thiếu (AD-2). Định nghĩa `Clause` dataclass (`kb/models.py`) = hợp đồng cho Epic 0 (AD-12) — bản Postgres sau này giữ nguyên chữ ký.
- `providers/llm.py` nạp `LLM_API_KEY` từ env, không dùng ở story này, không log key (AD-8).
- **Frontend**: cập nhật `chatApi.ts` — `SourceItem` thêm `clauseId`; `ChatResponse` thêm `conflictWarning`; gửi kèm `asOf`/`mode`; `parseSources` đọc `clause_id`; mock có `clauseId`. Giữ nguyên xử lý timeout 15s + lỗi CORS/JSON.
- Mock mode (`VITE_API_MODE=mock`) vẫn chạy độc lập (đường lui demo — NFR-3).
- Phạm vi giữ đúng "đường ống xanh": KHÔNG làm retrieve/temporal/LLM thật (để Story 1.2–1.5).

### File List

NEW:
- `backend/requirements.txt`
- `backend/.env.example`
- `backend/README.md`
- `backend/api/__init__.py`, `backend/api/main.py`
- `backend/kb/__init__.py`, `backend/kb/models.py`, `backend/kb/repository.py`
- `backend/providers/__init__.py`, `backend/providers/llm.py`
- `backend/pipeline/__init__.py`, `backend/ingest/__init__.py`
- `backend/tests/__init__.py`, `backend/tests/test_api.py`

UPDATE:
- `frontend/src/services/chatApi.ts` (thêm clauseId/conflictWarning, gửi asOf/mode)

## Change Log

- 2026-07-17: Story 1.1 — dựng đường ống xanh (FastAPI skeleton + `/api/chat` stub + repository stub đọc corpus + cập nhật chatApi.ts). 3 test pass, tsc/oxlint sạch. Status → review.
