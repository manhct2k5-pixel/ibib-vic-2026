---
baseline_commit: f12c67d723f79a905aad1904d0d41343906bb622
---

# Story 1.4: Lọc as-of + thay thế một phần + đánh dấu đã thay thế

Status: review

<!-- Ultimate context engine analysis completed - comprehensive developer guide created -->

## Story

As a cán bộ tuân thủ,
I want câu trả lời chỉ dùng bản CÒN HIỆU LỰC tại thời điểm hỏi, loại đúng khoản bị bãi bỏ một phần, và **đánh dấu rõ** điều nào đã bị thay thế,
so that tôi không áp nhầm quy định cũ và biết bản nào thay bản nào.

## Bối cảnh: phần lớn "lọc" đã có — story này bù phần còn thiếu
Lọc as-of + visibility đã nằm trong `repository.search` (Story 1.2), pipeline đã dùng (Story 1.3). Story 1.4 làm 3 việc CÒN THIẾU:
1. **As-of time-travel** end-to-end (chọn mốc quá khứ → ra bản khi đó) — FR-8 [Đầy đủ].
2. **Thay thế một phần** — xác nhận loại đúng khoản bị bãi bỏ, giữ phần còn lại — FR-9.
3. **Đánh dấu "đã thay thế"** cho các điều khoản trong tập ứng viên (đặc biệt điều bị `expand` kéo vào dù đã hết hiệu lực — follow-up từ Story 1.3), kèm "bị thay bởi bản nào".

## Acceptance Criteria

1. **As-of quá khứ đổi kết quả.** `POST /api/chat {question:"tỷ lệ an toàn vốn", asOf:"2019-06-01"}` → nguồn có `TT41/Điều 6.3` (8%), KHÔNG có `TT22/Điều 1` (9%, chưa hiệu lực lúc đó). Với `asOf` hôm nay thì ngược lại. (FR-8)
2. **Thay thế một phần.** Tại hôm nay, tập ứng viên/nguồn cho chủ đề báo cáo chứa `TT41/Điều 8.1` (còn hiệu lực) và KHÔNG chứa `TT41/Điều 8.2` như một điều còn hiệu lực (đã bị bãi bỏ). (FR-9)
3. **Đánh dấu đã thay thế.** Mỗi ứng viên được gắn trạng thái: `is_current` (còn hiệu lực tại as-of) và `superseded_by` (clause_id bản thay thế còn hiệu lực, nếu có). Điều bị `expand` kéo vào mà đã hết hiệu lực (VD `TT41/Điều 6.3`) phải có `is_current=false` + `superseded_by="TT22/Điều 1"`.
4. **Lộ ra API (additive).** `sources[]` thêm 2 trường **tùy chọn** `isCurrent: bool` và `supersededBy: string | null` (additive, không phá contract AD-6). `answer` stub nêu rõ nếu có nguồn đã bị thay thế.
5. **Một nguồn logic hiệu lực.** Không viết lại `is_active`; dùng lại hàm duy nhất (AD-5). "bị thay bởi bản nào" suy từ `repository.version_timeline` (không thêm SQL mới).

## Tasks / Subtasks

- [x]**Task 1 — Annotate trạng thái ứng viên** (AC: 3, 5)
  - [x]NEW `pipeline/annotate.py`: dataclass `CandidateView {clause: Clause, is_current: bool, superseded_by: str | None}` + hàm `annotate(repo, clauses, as_of) -> list[CandidateView]`
  - [x]`is_current` = `kb.repository.is_active(clause, as_of)` (tái dùng, AD-5)
  - [x]`superseded_by`: nếu không current, lấy từ `repo.version_timeline(clause_id)` — bản CÙNG topic/chuỗi còn hiệu lực tại as-of (nếu có), trả `clause_id` của nó
- [x]**Task 2 — Lộ trạng thái ra API** (AC: 4)
  - [x]UPDATE `api/main.py`: `Source` thêm `isCurrent: bool = True`, `supersededBy: str | None = None`; endpoint dùng `annotate(...)` để điền; `answer` nêu nếu có nguồn `is_current=false`
- [x]**Task 3 — Xác minh time-travel & thay thế một phần** (AC: 1, 2)
  - [x](Không cần code mới nếu search đã đúng) — nếu as-of quá khứ chưa đúng thì sửa; ghi rõ ở Debug Log
- [x]**Task 4 — Test**
  - [x]as-of 2019-06-01: nguồn có `TT41/Điều 6.3`, không có `TT22/Điều 1`
  - [x]as-of hôm nay: có `TT22/Điều 1`, `TT41/Điều 6.3` (nếu xuất hiện qua dẫn chiếu) có `isCurrent=false` + `supersededBy="TT22/Điều 1"`
  - [x]thay thế một phần: `TT41/Điều 8.1` current, `TT41/Điều 8.2` không current
  - [x]`annotate` gắn đúng `is_current`/`superseded_by`

## Dev Notes

### Bối cảnh Story 1.1–1.3 (tái dùng, đừng viết lại)
- ✅ `kb.repository.is_active(clause, as_of)` — hàm hiệu lực DUY NHẤT (AD-5). Import từ `kb.repository`.
- ✅ `repository.version_timeline(clause_id)` → list[Clause] theo thời gian (chuỗi SUPERSEDES). Dùng để suy `superseded_by`.
- ✅ `repository.search` đã lọc as-of + visibility. `pipeline/query.gather_candidates` đã gộp retrieve+expand.
- ✅ `api/main.py` endpoint đã parse `asOf`→date, gọi `gather_candidates`, build `sources`.
- ✅ `Source` model (clause_id, name, description) + frontend `chatApi.ts` (SourceItem có clauseId). **FE hiển thị trạng thái để Story 1.6** — story này chỉ thêm field vào API (additive), CHƯA sửa FE.
- ✅ 16 test đang pass — giữ nguyên.

### Cách suy `superseded_by`
`version_timeline(clause_id)` trả các phiên bản theo thời gian. Bản "thay thế" = phần tử trong timeline **còn hiệu lực tại as-of** (dùng `is_active`). VD timeline của `TT41/Điều 6.3` = [6.3 (2016–2023), TT22/Điều 1 (2023–nay)]; tại hôm nay bản active là `TT22/Điều 1` → `superseded_by="TT22/Điều 1"`.

### Guardrail
- **AD-5:** một `is_active`; không viết lại logic hiệu lực.
- **AD-6:** thêm field response phải **additive** (mặc định giữ tương thích). Không đổi request.
- **AD-7/12:** pipeline chỉ gọi repository + is_active helper; không SQL.
- **Phạm vi:** KHÔNG sửa frontend (Story 1.6), KHÔNG LLM (1.5), KHÔNG conflict (Epic 3).
- [Source: ARCHITECTURE-SPINE.md#AD-5,AD-6,AD-12]

### File sẽ chạm
| File | NEW/UPDATE |
|---|---|
| `pipeline/annotate.py` | NEW (`CandidateView` + `annotate`) |
| `api/main.py` | UPDATE (`Source` thêm field, endpoint dùng annotate) |
| `backend/tests/test_annotate.py` | NEW |

### Dữ liệu test (corpus.json)
- `TT41/Điều 6.3` (8%, 2016→2023) --SUPERSEDES--> ... thực ra edge: `TT22/Điều 1` SUPERSEDES `TT41/Điều 6.3`. timeline(6.3) gồm cả TT22/Điều 1.
- `TT41/Điều 8.1` (còn) / `TT41/Điều 8.2` (2016→2023, bị `TT22/Điều 2` thay).
- Mốc as-of 2019-06-01: 6.3 (8%) active, TT22/* chưa hiệu lực (eff 2023).

### Testing standards
- pytest; test `annotate` trực tiếp + endpoint qua TestClient (as-of quá khứ & hiện tại).
- `cd backend && source .venv/bin/activate && python -m pytest` — giữ 16 test cũ pass.

### References
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4 (FR-8, FR-9) + Story 1.3 follow-up note]
- [Source: ARCHITECTURE-SPINE.md#AD-5,AD-6]
- [Source: backend/kb/repository.py (is_active, version_timeline), backend/pipeline/query.py, backend/api/main.py]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (cc/claude-opus-4-8) — bmad-dev-story

### Debug Log References

- `pytest`: **21 passed** (16 cũ + 5 mới), không regression.
- As-of time-travel chạy đúng ngay (search đã as-of-aware từ Story 1.2) — Task 3 không cần code mới, chỉ thêm test xác minh.

### Completion Notes List

- **`pipeline/annotate.py`:** `CandidateView(clause, is_current, superseded_by)` + `annotate(repo, clauses, as_of)`. `is_current` = `is_active` (AD-5, tái dùng, không viết lại). `superseded_by` suy từ `repo.version_timeline` — phần tử còn hiệu lực tại as-of.
- **API additive (AD-6):** `Source` thêm `isCurrent: bool = True`, `supersededBy: str | None = None`. Request KHÔNG đổi. Endpoint dùng `annotate`, `answer` gắn cảnh báo nếu có nguồn đã thay thế.
- **Giải quyết follow-up Story 1.3:** điều dẫn chiếu đã hết hiệu lực (`TT41/Điều 6.3`) giờ được đánh dấu `isCurrent=false` + `supersededBy="TT22/Điều 1"` — không loại khỏi ngữ cảnh nhưng gắn nhãn rõ.
- **As-of time-travel (FR-8):** as-of 2019 → 8% (Điều 6.3), as-of nay → 9% (TT22/Điều 1). Test cả hai chiều.
- **Thay thế một phần (FR-9):** `TT41/Điều 8.1` current, `TT41/Điều 8.2` không phải nguồn còn hiệu lực.
- Phạm vi giữ đúng: KHÔNG sửa frontend (field additive để Story 1.6 hiển thị), KHÔNG LLM (1.5), KHÔNG conflict (Epic 3).

### File List

NEW:
- `backend/pipeline/annotate.py`
- `backend/tests/test_annotate.py`

UPDATE:
- `backend/api/main.py` (`Source` thêm isCurrent/supersededBy; endpoint dùng annotate + cảnh báo thay thế; import annotate)

## Change Log

- 2026-07-17: Story 1.4 — annotate trạng thái hiệu lực + as-of time-travel + đánh dấu "đã thay thế" (giải quyết follow-up 1.3). Field API additive. 21 test pass. Status → review.
