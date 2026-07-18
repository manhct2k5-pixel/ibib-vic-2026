---
baseline_commit: f12c67d723f79a905aad1904d0d41343906bb622
---

# Story 1.3: Retrieve + expand dẫn chiếu (pipeline)

Status: review

<!-- Ultimate context engine analysis completed - comprehensive developer guide created -->

## Story

As a nhân viên,
I want hệ thống tìm điều khoản liên quan và **tự kéo thêm điều được dẫn chiếu**,
so that câu trả lời không bỏ sót ngữ cảnh — và `/api/chat` trả về đúng các điều khoản thật (thay vì stub cứng của Story 1.1).

## Acceptance Criteria

1. **Tầng pipeline điều phối repository.** Có module `pipeline/` với 2 stage thuần: `retrieve(repo, question, as_of, mode) -> list[Clause]` (gọi `repo.search`) và `expand(repo, clauses) -> list[Clause]` (gọi `repo.expand_references`). Pipeline **không viết SQL, không gọi DB trực tiếp** — chỉ qua `repository` (AD-7, AD-12).
2. **Gộp + khử trùng lặp.** Một hàm điều phối `gather_candidates(repo, question, as_of, mode) -> list[Clause]` chạy retrieve → expand, **hợp nhất giữ thứ tự** (kết quả retrieve trước, điều dẫn chiếu thêm sau), **không trùng `clause_id`** (FR-5).
3. **Kéo đúng điều dẫn chiếu.** Câu hỏi khớp `TT41/Điều 10` (có REFERENCES tới `TT41/Điều 6.3`) → tập kết quả chứa cả `TT41/Điều 6.3`.
4. **Nối vào `/api/chat`.** Endpoint dùng `gather_candidates` (truyền `asOf`/`mode`), `sources` sinh từ điều khoản tìm được thật (clause_id + tên văn bản + trích đoạn). `answer` vẫn là **tóm tắt stub** liệt kê điều tìm được (LLM tổng hợp thật để ở Story 1.5). Rỗng kết quả → answer báo "không tìm thấy", `sources=[]`.
5. **as-of & mode truyền suốt.** `asOf` (mặc định hôm nay) và `mode` từ request đi thẳng vào `repo.search` — pipeline KHÔNG tự lọc hiệu lực/visibility (đã ở repository — AD-5/AD-11).

## Tasks / Subtasks

- [x]**Task 1 — Stage retrieve + expand** (AC: 1, 5)
  - [x]NEW `pipeline/retrieve.py`: `retrieve(repo, question, as_of, mode="system") -> list[Clause]` = `repo.search(question, as_of, mode)`
  - [x]NEW `pipeline/expand.py`: `expand(repo, clauses) -> list[Clause]` = `repo.expand_references([c.clause_id for c in clauses])`
- [x]**Task 2 — Điều phối gather_candidates** (AC: 2, 3)
  - [x]NEW `pipeline/query.py`: `gather_candidates(repo, question, as_of, mode="system") -> list[Clause]` — retrieve → expand → hợp nhất giữ thứ tự + khử trùng theo `clause_id`
- [x]**Task 3 — Nối vào /api/chat** (AC: 4, 5)
  - [x]UPDATE `api/main.py`: endpoint parse `asOf` (mặc định hôm nay, dạng `date`), gọi `gather_candidates`, build `sources` từ kết quả, `answer` = tóm tắt stub (liệt kê `path` + `doc_title`), xử lý rỗng
  - [x]Bỏ dùng `repo.any_clause()` trong endpoint (helper ngoài Protocol) — thay bằng kết quả pipeline
- [x]**Task 4 — Test** (AC: 2, 3, 4)
  - [x]`gather_candidates` cho câu hỏi khớp Điều 10 → có cả `TT41/Điều 6.3` (dẫn chiếu)
  - [x]`gather_candidates` không trùng `clause_id`
  - [x]`POST /api/chat` với câu hỏi CAR → 200, `sources` chứa `clause_id` thật, không có clause hết hạn (`TT41/Điều 6.3` không phải nguồn chính khi hỏi CAR)
  - [x]`POST /api/chat` câu hỏi vô nghĩa → `sources=[]`, answer báo không tìm thấy

## Dev Notes

### Bối cảnh từ Story 1.2 (đã làm — TÁI SỬ DỤNG, đừng viết lại)
- ✅ `repository.search(q, as_of, mode)` đã lọc hiệu lực (AD-5) + visibility (AD-11) + khớp từ khóa, trả `list[Clause]` sắp theo liên quan. **Retrieve stage chỉ gọi lại nó.**
- ✅ `repository.expand_references(clause_ids)` trả các Clause được REFERENCES. **Expand stage chỉ gọi lại nó.**
- ✅ `Repository` Protocol + `get_repository()` factory + `app.state.repo` đã có. Pipeline nhận `repo: Repository` làm tham số.
- ✅ `Clause` dataclass (khóa `clause_id`), `Source` model trong `api/main.py`.
- ✅ Endpoint hiện dùng `repo.any_clause()` (green-pipe Story 1.1) — **story này thay bằng pipeline thật**.
- ✅ 10 test đang pass — không được phá.

### ⚠️ Quan hệ với Story 1.4 (temporal) — tránh trùng
Lọc hiệu lực **đã nằm trong `repository.search`** (as-of). Story 1.3 KHÔNG lọc lại. Story 1.4 sẽ lo *hiển thị/xác minh* thay thế một phần + cho chọn as-of quá khứ, không phải viết lại lọc.

### Guardrail kiến trúc
- **AD-3:** pipeline là stage điều phối; thứ tự retrieve → expand (→ temporal đã trong search → conflict ở Story 3 → synthesize ở 1.5).
- **AD-7/AD-12:** `pipeline` chỉ import `repository` + `Clause`; KHÔNG psycopg/SQL.
- **AD-6:** giữ contract `/api/chat`; `sources[].clause_id` bắt buộc.
- [Source: ARCHITECTURE-SPINE.md#AD-3,AD-6,AD-7,AD-12]

### File sẽ chạm
| File | NEW/UPDATE |
|---|---|
| `pipeline/retrieve.py` | NEW |
| `pipeline/expand.py` | NEW |
| `pipeline/query.py` | NEW (gather_candidates) |
| `api/main.py` | UPDATE (dùng pipeline, parse asOf→date, bỏ any_clause) |
| `backend/tests/test_pipeline.py` | NEW |

### Lưu ý parse asOf
Request `asOf` là chuỗi `YYYY-MM-DD` (hoặc null → hôm nay). Endpoint chuyển sang `datetime.date` trước khi truyền vào pipeline/repository. Sai định dạng → HTTP 422 (Pydantic) hoặc 400 + `detail`.

### Phạm vi — KHÔNG làm quá
KHÔNG gọi LLM (answer vẫn stub — Story 1.5). KHÔNG làm conflict banner (Epic 3). KHÔNG đụng frontend. KHÔNG viết lại repository.

### Dữ liệu test (corpus.json)
- `TT41/Điều 10` --REFERENCES--> `TT41/Điều 6.3`
- Hỏi "vốn tự có" → khớp Điều 10 → expand kéo Điều 6.3
- Hỏi "tỷ lệ an toàn vốn" hôm nay → `TT22/Điều 1` (9%), KHÔNG `TT41/Điều 6.3` (hết hạn)

### Testing standards
- pytest; test pipeline trực tiếp (truyền repo từ `get_repository`) + test endpoint qua TestClient.
- `cd backend && source .venv/bin/activate && python -m pytest` — giữ 10 test cũ pass.

### References
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3 (FR-5)]
- [Source: ARCHITECTURE-SPINE.md#AD-3,AD-12]
- [Source: backend/kb/repository.py, backend/kb/repository_protocol.py, backend/api/main.py (Story 1.2)]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (cc/claude-opus-4-8) — bmad-dev-story

### Debug Log References

- `pytest` (backend): **16 passed** (10 cũ + 6 mới), không regression.
- 1 test ban đầu (`TT41/Điều 6.3 not in sources`) fail vì assumption sai phạm vi — đã sửa: `retrieve` trực tiếp loại 6.3 (temporal đúng), nhưng `expand` kéo 6.3 qua dẫn chiếu từ Điều 10 (đúng FR-5). Test đổi sang kiểm `retrieve` loại 6.3 + bản 9% có mặt.

### Completion Notes List

- **Tầng pipeline (AD-3):** `pipeline/retrieve.py` (gọi `repo.search`), `pipeline/expand.py` (gọi `repo.expand_references`), `pipeline/query.py::gather_candidates` (retrieve → expand, hợp nhất giữ thứ tự + khử trùng `clause_id`). Chỉ gọi repository, không SQL (AD-7/AD-12).
- **Nối `/api/chat`:** endpoint parse `asOf` (chuỗi → `date`, sai định dạng → 400 + detail), gọi `gather_candidates`, `sources` sinh từ điều khoản thật (`clause_id` + `doc_code — path` + trích đoạn). Bỏ `repo.any_clause()` (helper green-pipe). Rỗng → answer "Không tìm thấy", `sources=[]`. `answer` vẫn tóm tắt stub (LLM ở Story 1.5).
- **as-of/mode truyền suốt** vào `repo.search`; pipeline không lọc lại (AD-5/AD-11).
- **[NOTE FOR Story 1.4]** `expand` hiện kéo cả điều dẫn chiếu ĐÃ HẾT HIỆU LỰC (VD Điều 10 → Điều 6.3 8% cũ). Story 1.4/1.6 cần **đánh dấu** những điều này là "đã thay thế" khi hiển thị (không loại khỏi context, nhưng phải gắn nhãn) — hoặc cân nhắc để `find`/synthesize ưu tiên bản hiện hành. Dữ liệu corpus nên có 1 ca dẫn chiếu tới điều CÒN hiệu lực để demo FR-5 sạch hơn (Epic 0.2).
- Phạm vi giữ đúng: KHÔNG LLM, KHÔNG conflict/FE, KHÔNG viết lại repository.

### File List

NEW:
- `backend/pipeline/retrieve.py`
- `backend/pipeline/expand.py`
- `backend/pipeline/query.py`
- `backend/tests/test_pipeline.py`

UPDATE:
- `backend/api/main.py` (parse asOf→date, gọi gather_candidates, sources thật, bỏ any_clause, thêm import HTTPException/date/pipeline; bỏ import Path không dùng)

## Change Log

- 2026-07-17: Story 1.3 — tầng pipeline retrieve+expand điều phối repository + nối `/api/chat` trả điều khoản thật. 16 test pass. Status → review. (Ghi chú follow-up cho 1.4: đánh dấu điều dẫn chiếu đã hết hiệu lực.)
