---
baseline_commit: f12c67d723f79a905aad1904d0d41343906bb622
---

# Story 1.7: Chế độ khách hàng (công khai)

Status: review

<!-- Ultimate context engine analysis completed - comprehensive developer guide created -->

## Story

As a khách hàng,
I want tra cứu quy định công khai qua cùng giao diện,
so that tôi được trả lời mà KHÔNG chạm dữ liệu nội bộ của ngân hàng.

## Quyết định thiết kế D1 (chốt từ code-review) — TÁCH 2 trục
Code-review phát hiện `mode` đang gộp 2 trục: **benchmark** (`system`/`baseline`) và **người dùng** (nhân viên/khách hàng), khiến lọc visibility (AD-11) không bao giờ chạy. **Chốt:** tách thành 2 khái niệm độc lập:
- **`audience`** (mới, request field): `"employee"` (mặc định) | `"customer"`. Quyết định phạm vi dữ liệu.
- **`scope`** (nội bộ, tham số của `repository.search`): `"all"` | `"public"` — đổi tên từ `mode` cũ để đúng ngữ nghĩa visibility.
- **`mode`** (`system`/`baseline`) vẫn dành cho benchmark (Epic 4), KHÔNG dùng cho visibility nữa.

## Acceptance Criteria

1. **Request thêm `audience` (additive).** `POST /api/chat` nhận thêm `audience: "employee" | "customer"` (mặc định `employee`). `employee` → thấy cả internal; `customer` → chỉ public. Không đổi field cũ (AD-6 additive).
2. **`repository.search` dùng `scope` (đổi tên từ `mode`).** `search(q, as_of, scope="all")`: `scope="public"` chỉ trả clause `visibility="public"` (AD-11). Cập nhật `Repository` Protocol + mọi caller (retrieve/query/endpoint) + test cũ (`mode="public"` → `scope="public"`).
3. **`expand` không vượt sang internal khi customer.** `expand_references` nhận `scope`; ở `scope="public"`, KHÔNG trả clause `internal`. Không rò nội bộ qua dẫn chiếu (AD-11).
4. **Endpoint suy `scope` từ `audience`.** `scope = "public" if audience=="customer" else "all"`; truyền xuống `gather_candidates`. Mọi `sources` ở chế độ khách hàng đều `visibility="public"` — `QD-INT/Điều 2` (internal) KHÔNG xuất hiện.
5. **Frontend ModeToggle (UX-DR10).** Thanh trên có toggle **Nhân viên / Khách hàng** → gửi `audience`; ở Khách hàng, nhãn "Chế độ công khai" (màu public). Đổi toggle → tra lại câu hỏi cuối (như AsOfPicker).

## Tasks / Subtasks

- [x]**Task 1 — Đổi tên `mode`→`scope` trong repository (AC: 2, 3)**
  - [x]UPDATE `kb/repository_protocol.py`: `search(q, as_of, scope="all")`; `expand_references(clause_ids, scope="all")`
  - [x]UPDATE `kb/repository.py` StubRepository: `search` lọc `visibility="public"` khi `scope=="public"`; `expand_references` bỏ clause internal khi `scope=="public"`
  - [x]UPDATE tests cũ dùng `mode="public"` → `scope="public"` (`test_repository.py`)
- [x]**Task 2 — Pipeline truyền scope (AC: 4)**
  - [x]UPDATE `pipeline/retrieve.py`, `pipeline/expand.py`, `pipeline/query.py`: nhận + truyền `scope` (thay tham số `mode` cũ nếu có)
- [x]**Task 3 — Endpoint audience→scope (AC: 1, 4)**
  - [x]UPDATE `api/main.py`: `ChatRequest` thêm `audience: str | None = "employee"`; suy `scope`; truyền vào `gather_candidates`; (giữ `mode` cho benchmark, chưa dùng)
- [x]**Task 4 — Frontend ModeToggle (AC: 5)**
  - [x]UPDATE `chatApi.ts`: `ChatOptions` thêm `audience`; gửi kèm body
  - [x]UPDATE `App.tsx`: state `audience`; ModeToggle Nhân viên/Khách hàng; nhãn "Chế độ công khai"; đổi toggle tra lại
  - [x]UPDATE `App.css`: style toggle
- [x]**Task 5 — Test**
  - [x]`search(scope="public")`: không trả `QD-INT/Điều 2`
  - [x]`expand_references([...], scope="public")`: không kéo clause internal
  - [x]`/api/chat` `audience="customer"`: mọi `sources` là public, không có `QD-INT/Điều 2`
  - [x]`/api/chat` `audience="employee"` (mặc định): vẫn thấy internal

## Dev Notes

### Bối cảnh (đọc kỹ — tránh phá)
- ✅ `repository.search(q, as_of, mode="system")` HIỆN lọc public khi `mode=="public"` (Story 1.2) — nhưng không ai truyền "public" → dead code (chính là D1). Story này **đổi tên `mode`→`scope`** và **nối đúng** qua `audience`.
- ✅ `expand_references(clause_ids)` HIỆN không lọc visibility — cần thêm `scope` để không rò internal.
- ✅ `pipeline/retrieve.py` gọi `repo.search(question, as_of, mode)`; `gather_candidates` truyền `mode`. Đổi sang `scope`.
- ✅ `api/main.py`: `ChatRequest{question, asOf, mode}`; endpoint truyền `mode` vào gather. Thêm `audience`, suy `scope`.
- ✅ `chatApi.ts`: `ChatOptions{asOf, mode}` + gửi body. Thêm `audience`.
- ✅ `App.tsx`: đã có AsOfPicker + runQuery(q, when). Thêm `audience` tương tự (đổi → tra lại).
- ✅ 25 test BE + FE build đang xanh — giữ nguyên; test cũ `mode="public"` phải đổi sang `scope="public"` kẻo fail.

### ⚠️ Cẩn thận đổi tên tránh vỡ
`repository.search` được gọi ở `pipeline/retrieve.py`. `find_conflicts`/`version_timeline`/`export_graph` KHÔNG liên quan visibility scope — đừng đụng. Chỉ `search` + `expand_references` thêm `scope`.

### Guardrail
- **AD-11:** lọc visibility trong repository (`search`/`expand`), không ở tầng trên.
- **AD-6:** `audience` là field additive; mặc định `employee` giữ hành vi cũ.
- **AD-12:** không SQL ngoài repository.
- **Phạm vi:** KHÔNG đụng benchmark `mode` (Epic 4); KHÔNG GraphPanel (Epic 2).
- [Source: ARCHITECTURE-SPINE.md#AD-6,AD-11,AD-12; code-review Story 1.6 D1]

### File sẽ chạm
| File | NEW/UPDATE |
|---|---|
| `kb/repository_protocol.py` | UPDATE (search/expand thêm scope) |
| `kb/repository.py` | UPDATE (scope filter) |
| `pipeline/retrieve.py`, `expand.py`, `query.py` | UPDATE (truyền scope) |
| `api/main.py` | UPDATE (audience→scope) |
| `frontend/src/services/chatApi.ts` | UPDATE (audience) |
| `frontend/src/App.tsx`, `App.css` | UPDATE (ModeToggle) |
| `backend/tests/test_repository.py` | UPDATE (mode→scope) |
| `backend/tests/test_audience.py` | NEW |

### Dữ liệu test (corpus.json)
- `QD-INT/Điều 2` là clause **internal** duy nhất (topic ty_le_an_toan_von, 8%) — dùng để kiểm không rò ở chế độ khách hàng.
- Các clause TT41/TT22 đều `public`.

### Testing standards
- Backend: pytest — giữ 25 test cũ (sau khi đổi mode→scope). Frontend: tsc + oxlint + build sạch.

### References
- [Source: epics.md#Story 1.7 (FR-7); ARCHITECTURE-SPINE.md#AD-11]
- [Source: code-review Story 1.6 finding D1 (mode lệch trục)]
- [Source: backend/kb/repository.py, pipeline/*, api/main.py; frontend/src/App.tsx, chatApi.ts]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (cc/claude-opus-4-8) — bmad-dev-story

### Debug Log References

- `pytest`: **29 passed** (25 + 4 mới). FE tsc/oxlint/build: exit 0.

### Completion Notes List

- **Chốt D1 (tách 2 trục):** thêm request `audience` (employee|customer); đổi tên tham số visibility `mode`→`scope` (all|public) trong `repository.search`/`expand_references` + Protocol + mọi caller pipeline; giữ `mode` (system/baseline) cho benchmark riêng.
- **Không rò nội bộ (AD-11):** endpoint suy `scope="public"` khi `audience=="customer"`; `search` và `expand_references` đều lọc `visibility="public"` → `QD-INT/Điều 2` (internal) không lọt ra ở chế độ khách hàng. Test cả 2 chiều (customer loại internal, employee thấy internal).
- **Frontend ModeToggle:** Nhân viên/Khách hàng ở thanh trên → gửi `audience`; nhãn "Chế độ công khai" (màu public) khi Khách hàng; đổi toggle tra lại câu hỏi cuối (dùng lại race guard của 1.6).
- **Contract:** `API_CONTRACT.md` thêm field `audience` (additive).
- Đổi test cũ `mode="public"`→`scope="public"` (test_repository) — giữ xanh.
- Phạm vi giữ đúng: KHÔNG đụng benchmark `mode` (Epic 4), KHÔNG GraphPanel (Epic 2).

### File List

NEW:
- `backend/tests/test_audience.py`

UPDATE:
- `backend/kb/repository_protocol.py`, `backend/kb/repository.py` (mode→scope, expand lọc internal)
- `backend/pipeline/retrieve.py`, `expand.py`, `query.py` (truyền scope)
- `backend/api/main.py` (ChatRequest.audience → scope)
- `backend/tests/test_repository.py` (mode→scope)
- `frontend/src/services/chatApi.ts` (ChatOptions.audience)
- `frontend/src/App.tsx` (ModeToggle, audience state)
- `frontend/src/App.css` (mode-toggle, public-tag)
- `docs/architecture/API_CONTRACT.md` (audience)

## Change Log

- 2026-07-18: Story 1.7 — chế độ khách hàng: tách trục audience (employee/customer) khỏi benchmark mode, đổi `mode→scope` trong repository, ModeToggle FE. Giải quyết D1. 29 test pass, FE sạch. Status → review.
- 2026-07-18: Code-review fixes — **fail-closed** audience→scope (chỉ 'employee' chính xác thấy nội bộ); `annotate` nhận scope → không lộ `superseded_by` internal cho khách hàng (AD-11 defense-in-depth); `handleClear` reset audience; sửa comment schema.sql (mode→scope). 29 test pass, tsc/oxlint sạch. Status → done.
- **[DEFER cho Epic 3/FR-12]** `find_conflicts`/`export_graph` chưa nhận `scope` — PHẢI thêm khi nối vào chế độ khách hàng, kẻo rò dữ liệu nội bộ.
