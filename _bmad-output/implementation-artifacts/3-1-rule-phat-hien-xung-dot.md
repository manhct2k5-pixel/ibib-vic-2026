---
baseline_commit: 1c491229811d277a45b6a292607d206410ce946d
---

# Story 3.1: Rule phát hiện xung đột

Status: review

<!-- Ultimate context engine analysis completed - comprehensive developer guide created -->

## Story

As a hệ thống,
I want quét dữ liệu để phát hiện điều khoản cùng chủ đề, cùng hiệu lực nhưng khác giá trị số,
so that cảnh báo được mâu thuẫn thật (không hardcode).

## Acceptance Criteria

1. **Stage `conflict_check` (AD-3).** Thêm stage `pipeline/conflict_check.py` chạy SAU `temporal_filter` (lọc hiệu lực đã nằm trong `search`) và TRƯỚC `synthesize`. Stage gọi `repository.find_conflicts(as_of)` — KHÔNG tự quét/parse ở tầng pipeline (AD-12).
2. **Rule quét thật (NFR-7).** Với các clause **cùng còn hiệu lực** tại `as_of`, cùng `topic`, cùng `metric_unit`, khác `metric_value` → gắn cờ xung đột. Phát hiện `TT22/Điều 1` (9%) vs `QD-INT/Điều 2` (8%). Rule tổng quát, chịu được ≥1 ca dựng thêm không xem trước (không hardcode clause_id).
3. **"Bản cũ vs bản mới" KHÔNG phải xung đột.** `TT41/Điều 6.3` (8%, hết hiệu lực 2023) so với `TT22/Điều 1` (9%) KHÔNG bị gắn cờ — vì 6.3 không còn active (đã do lọc hiệu lực xử, AD-3/AD-5).
4. **Chỉ cảnh báo xung đột LIÊN QUAN câu hỏi.** Chỉ set `conflictWarning` khi cặp xung đột có `topic` thuộc tập candidate của câu trả lời — không cảnh báo mâu thuẫn ở chủ đề người dùng không hỏi.
5. **Endpoint trả `conflictWarning` (AD-6).** `/api/chat` set `conflictWarning` = chuỗi mô tả (liệt kê 2 nguồn + giá trị) khi có xung đột liên quan; `null` khi không. Không đổi field khác.
6. **Không rò nội bộ khi customer (AD-11).** `find_conflicts` nhận `scope`; ở `scope="public"` bỏ clause `internal` khỏi so sánh → `audience=customer` KHÔNG thấy cảnh báo dính `QD-INT/Điều 2`.

## Tasks / Subtasks

- [x] **Task 1 — find_conflicts nhận scope (AC: 6)**
  - [x] UPDATE `kb/repository_protocol.py` + `kb/repository.py`: `find_conflicts(as_of, scope="all")` — khi `scope="public"` bỏ clause `visibility != "public"` khỏi tập ứng viên
  - [x] Test: `find_conflicts(TODAY, scope="public")` KHÔNG có cặp dính `QD-INT/Điều 2`; `scope="all"` vẫn có
- [x] **Task 2 — Stage conflict_check (AC: 1, 2, 3, 4)**
  - [x] NEW `pipeline/conflict_check.py`: `check_conflicts(repo, candidates, as_of, scope="all") -> str | None` — gọi `repo.find_conflicts(as_of, scope)`, lọc cặp có `topic` ∈ `{c.topic for c in candidates}`, build chuỗi cảnh báo tiếng Việt (liệt kê 2 nguồn + giá trị + đơn vị); không có → `None`
  - [x] Test: candidate chứa `ty_le_an_toan_von` (employee) → trả chuỗi có `TT22/Điều 1` + `QD-INT/Điều 2`; candidate chủ đề khác → `None`; bản cũ 6.3 không gây cờ
- [x] **Task 3 — Wiring endpoint (AC: 5, 6)**
  - [x] UPDATE `api/main.py`: sau `annotate`, gọi `check_conflicts(repo, clauses, as_of, scope)`; đặt vào `ChatResponse.conflictWarning`
  - [x] Test: `/api/chat` câu hỏi an toàn vốn (employee) → `conflictWarning` khác null, nêu 2 nguồn; `audience=customer` → `conflictWarning` null (không rò internal)
- [x] **Task 4 — Kiểm tra**
  - [x] Backend: pytest giữ 35 test cũ + test mới conflict (41 passed)
  - [x] Frontend: KHÔNG cần đổi (ConflictBanner đã có từ Epic 1)

## Dev Notes

### Bối cảnh (tái dùng — Epic 1 đã có sẵn phần lớn)
- ✅ `repository.find_conflicts(as_of)` ĐÃ có (Story 1.2) và ĐÚNG: chỉ xét clause `is_active(c, as_of)` + `metric_value is not None`; ghép cặp cùng `topic` + **cùng `metric_unit`** + khác `metric_value`; trả `list[ConflictPair]`. Test `test_find_conflicts_detects_pair` đã xác nhận bắt được `frozenset(("TT22/Điều 1","QD-INT/Điều 2"))`. **CHƯA nhận scope** → story này thêm.
- ✅ `ConflictPair` dataclass (`kb/models.py`): `clause_a, clause_b, topic, value_a, value_b, unit`. Dùng để build chuỗi cảnh báo.
- ✅ `ConflictBanner` FE ĐÃ có (Epic 1): `App.tsx` render `.conflict-banner` (amber + ⚠) khi `conflictWarning?.trim()`; `App.css` đã style. **KHÔNG cần đụng FE** cho story này — chỉ cần backend trả chuỗi.
- ✅ `api/main.py`: `/api/chat` hiện luôn trả `conflictWarning=None` (dòng cuối `ChatResponse(...)`). Đây là chỗ wiring.
- ✅ `pipeline/query.py` `gather_candidates(...)` trả `list[Clause]` candidate; endpoint đã có `clauses` + `views` (annotate) + `scope`. Chèn `check_conflicts` giữa annotate và build response.
- ✅ 35 test BE xanh — giữ nguyên.

### find_conflicts — hành vi hiện tại (đọc kỹ trước khi sửa)
- `kb/repository.py` `find_conflicts(as_of)`: `candidates = [c for c in self._clauses if is_active(c, as_of) and c.metric_value is not None]`; vòng đôi so `a.topic==b.topic and a.metric_unit==b.metric_unit and a.metric_value!=b.metric_value`.
- **Phải giữ:** điều kiện `is_active` (đảm bảo AC-3: bản cũ hết hiệu lực không tạo xung đột giả) và `metric_unit` (P4: khác đơn vị không so).
- **Thêm scope:** khi `scope="public"`, thêm điều kiện `c.visibility == "public"` vào bộ lọc `candidates` (bỏ internal) — không rò `QD-INT/Điều 2` cho khách hàng (AD-11).

### Guardrail
- **AD-3:** `conflict_check` là stage cố định sau temporal, trước synthesize; input/output rõ (`candidates → conflictWarning`).
- **AD-12:** phát hiện xung đột nằm trong `repository.find_conflicts`; pipeline chỉ điều phối + định dạng thông điệp, KHÔNG tự quét clause.
- **AD-5:** "còn hiệu lực" chỉ qua `is_active` (đã dùng trong find_conflicts) — không viết lại.
- **AD-11:** lọc visibility trong repository (`find_conflicts` scope), không ở tầng trên.
- **AD-6:** `conflictWarning` là field đã có trong contract (Epic 1) — chỉ điền giá trị, không đổi shape.
- **NFR-7:** rule tổng quát (quét cặp), KHÔNG hardcode `TT22`/`QD-INT`.
- **Phạm vi — KHÔNG làm quá:** tinh chỉnh banner (nút "xem chi tiết", liệt kê đẹp) là **Story 3.2**. Story này chỉ: rule scope + stage + wiring để `conflictWarning` khác null đúng lúc.
- [Source: epics.md#Story 3.1 (FR-11, NFR-7); ARCHITECTURE-SPINE.md#AD-3 (thứ tự conflict vs temporal), AD-5, AD-11, AD-12; EXPERIENCE.md ConflictBanner]

### File sẽ chạm
| File | NEW/UPDATE |
|---|---|
| `backend/kb/repository_protocol.py`, `repository.py` | UPDATE (find_conflicts scope) |
| `backend/pipeline/conflict_check.py` | NEW (stage check_conflicts) |
| `backend/api/main.py` | UPDATE (wiring conflictWarning) |
| `backend/tests/test_conflict.py` | NEW |

### Dữ liệu (corpus.json — đã xác minh)
- Xung đột thật: `TT22/Điều 1` (ty_le_an_toan_von, 9%, active, **public**) vs `QD-INT/Điều 2` (ty_le_an_toan_von, 8%, active, **internal**). Cùng topic + cùng đơn vị `%` + khác value → cờ.
- Không xung đột: `TT41/Điều 6.3` (8%, **hết hiệu lực** 2023) — bị loại vì không active → không tạo cờ giả với TT22/Điều 1 (AC-3).
- Ở `scope="public"`: bỏ `QD-INT/Điều 2` (internal) → KHÔNG còn cặp xung đột ty_le_an_toan_von → customer không thấy cảnh báo (AC-6).

### Ví dụ chuỗi cảnh báo (gợi ý, không bắt buộc từng chữ)
`"Phát hiện xung đột: TT22/Điều 1 (9%) và QD-INT/Điều 2 (8%) cùng chủ đề 'ty_le_an_toan_von' và cùng còn hiệu lực. Vui lòng kiểm tra trước khi áp dụng."`

### Testing standards
- Backend pytest (giữ 35 + mới). Kiểm thủ công: hỏi "tỷ lệ an toàn vốn tối thiểu?" (employee) → banner ⚠ hiện; đổi sang Khách hàng → banner biến mất.

### References
- [Source: epics.md#Story 3.1 (FR-11, NFR-7); ARCHITECTURE-SPINE.md#AD-3,AD-5,AD-11,AD-12]
- [Source: backend/kb/repository.py (find_conflicts, is_active), kb/models.py (ConflictPair), api/main.py, pipeline/query.py]
- [Source: ux-designs/.../EXPERIENCE.md (ConflictBanner — đã hiện thực Epic 1)]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (cc/claude-opus-4-8) — bmad-dev-story

### Debug Log References

- Backend `pytest`: **41 passed** (35 cũ + 6 mới `test_conflict.py`), 0.23s.
- FE không đổi (ConflictBanner có sẵn từ Epic 1).

### Completion Notes List

- **Task 1 — find_conflicts scope:** thêm `scope="all"` vào Protocol + `StubRepository`; `scope="public"` thêm điều kiện `c.visibility == "public"` vào bộ lọc candidate → không so clause internal (AD-11). Giữ nguyên `is_active` + `metric_unit` (không phá AC-3/P4).
- **Task 2 — Stage conflict_check:** NEW `pipeline/conflict_check.py` `check_conflicts(repo, candidates, as_of, scope)` — gọi `repo.find_conflicts(as_of, scope)` (quét thật, AD-12), lọc cặp có `topic ∈ candidate topics` (AC-4: chỉ cảnh báo mâu thuẫn liên quan câu hỏi), build chuỗi tiếng Việt liệt kê 2 nguồn + giá trị + đơn vị. Không có cặp liên quan → `None`.
- **Task 3 — Wiring:** `api/main.py` gọi `check_conflicts` sau `annotate`, đặt kết quả vào `ChatResponse.conflictWarning` (trước đây hard-code `None`). ConflictBanner FE tự hiện khi khác null.
- **AC-3 tự thỏa (không cần code thêm):** `TT41/Điều 6.3` (8%, hết hiệu lực 2023) bị `is_active` loại → không tạo xung đột giả với `TT22/Điều 1` (9%). "Bản cũ vs mới" = thay thế, không phải mâu thuẫn.
- **AC-6:** `audience=customer` → `scope="public"` → QD-INT (internal) bị loại → không còn cặp xung đột ty_le_an_toan_von → `conflictWarning=null` (không rò nội bộ).
- **NFR-7:** rule tổng quát trong `find_conflicts` (quét cặp cùng topic+unit, khác value) — KHÔNG hardcode clause_id.
- **Phạm vi giữ đúng:** KHÔNG tinh chỉnh banner (nút "xem chi tiết") — để Story 3.2.

### File List

NEW:
- `backend/pipeline/conflict_check.py`
- `backend/tests/test_conflict.py`

UPDATE:
- `backend/kb/repository_protocol.py` (find_conflicts nhận scope)
- `backend/kb/repository.py` (find_conflicts lọc internal khi public)
- `backend/api/main.py` (wiring conflictWarning qua check_conflicts)

## Change Log

- 2026-07-18: Story 3.1 — rule phát hiện xung đột. Thêm scope cho `find_conflicts` (AD-11), stage `conflict_check` (AD-3) lọc theo chủ đề candidate, wiring `conflictWarning` vào `/api/chat`. Employee thấy cảnh báo 9% vs 8%; customer không rò internal. 41 test pass, FE không đổi (banner có sẵn). Status → review.
