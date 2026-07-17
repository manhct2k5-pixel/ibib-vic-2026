---
baseline_commit: 1c491229811d277a45b6a292607d206410ce946d
---

# Story 3.2: Hiển thị banner cảnh báo xung đột

Status: review

## Story

As a nhân viên,
I want thấy cảnh báo rõ khi có xung đột,
so that tôi thận trọng trước khi áp dụng.

## Acceptance Criteria

1. **Banner khi có xung đột (FR-13, UX-DR6).** `conflictWarning` khác null → hiện ConflictBanner: nền amber, icon ⚠. (Đã có từ Epic 1 — giữ.)
2. **Không chiếm toàn màn + "xem chi tiết".** Banner mặc định gọn (1 dòng tóm tắt); có nút "Xem chi tiết" bung/thu phần mô tả đầy đủ (liệt kê 2 nguồn mâu thuẫn + giá trị). Không đẩy văn bản chiếm cả khối kết quả.
3. **A11y.** Nút toggle có `aria-expanded`; trạng thái không chỉ bằng màu (kèm icon ⚠ + chữ).

## Tasks / Subtasks

- [x] **Task 1 — Banner có toggle chi tiết (AC: 2, 3)**
  - [x] UPDATE `frontend/src/App.tsx`: banner hiện dòng tóm tắt cố định + nút "Xem chi tiết" (`aria-expanded`); bung ra `conflictWarning` đầy đủ. State `showConflictDetail` (reset khi query mới + Xóa).
  - [x] UPDATE `frontend/src/App.css`: nút toggle trong `.conflict-banner`; layout gọn (summary + detail thu/mở)
- [x] **Task 2 — Kiểm tra**
  - [x] Frontend: `tsc -b` + `oxlint` + `vite build` sạch
  - [x] Backend: KHÔNG đổi — pytest 41 vẫn xanh

## Dev Notes

### Bối cảnh (tái dùng)
- ✅ ConflictBanner ĐÃ có (Epic 1) trong `App.tsx`: `{conflictWarning?.trim() && (<div className="conflict-banner"><span aria-hidden>⚠</span><span>{conflictWarning}</span></div>)}`. `App.css` `.conflict-banner` đã amber (`#fef3e2`) + viền `--conflict` + icon.
- ✅ Story 3.1 (đã xong) đã điền `conflictWarning` = chuỗi liệt kê 2 nguồn + giá trị (VD "Phát hiện xung đột: TT22/Điều 1 (9%) và QD-INT/Điều 2 (8%)...").
- Story này CHỈ đổi FE: chuyển banner từ "hiện full text" sang "tóm tắt + nút Xem chi tiết bung full text".

### Guardrail
- **KHÔNG đụng backend** — `conflictWarning` giữ nguyên (contract AD-6). 3.1 đã sinh chuỗi.
- **KHÔNG rò internal:** chuỗi `conflictWarning` do backend quyết định (customer đã null từ 3.1) — FE chỉ hiển thị.
- **Phạm vi:** chỉ toggle chi tiết + gọn. KHÔNG thêm liên kết sang đồ thị (2.3).
- [Source: epics.md#Story 3.2 (FR-13, UX-DR6); EXPERIENCE.md ConflictBanner; App.tsx/App.css hiện có]

### File sẽ chạm
| File | NEW/UPDATE |
|---|---|
| `frontend/src/App.tsx` | UPDATE (toggle chi tiết) |
| `frontend/src/App.css` | UPDATE (style nút + gọn) |

### Testing standards
- Frontend tsc/oxlint/build. Kiểm thủ công: hỏi câu an toàn vốn → banner gọn + nút "Xem chi tiết" bung ra full.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (cc/claude-opus-4-8) — bmad-dev-story

### Debug Log References

- Frontend: `tsc -b` + `oxlint` (exit 0) + `vite build` sạch. Backend `pytest`: 41 passed (không đổi).

### Completion Notes List

- **Banner gọn + toggle:** ConflictBanner (đã có từ Epic 1) giờ hiện dòng tóm tắt cố định "Phát hiện xung đột giữa các quy định cùng hiệu lực." + nút "Xem chi tiết / Thu gọn" (`aria-expanded`) bung ra chuỗi `conflictWarning` đầy đủ (2 nguồn + giá trị do Story 3.1 sinh). Mặc định thu → không chiếm khối kết quả.
- **A11y:** nút có `aria-expanded`; cảnh báo vẫn kèm icon ⚠ + chữ (không chỉ màu); focus ring amber.
- **State sạch:** `showConflictDetail` reset về false khi query mới và khi bấm Xóa (không giữ trạng thái bung giữa các câu hỏi).
- **KHÔNG đụng backend** — contract `conflictWarning` giữ nguyên; customer vẫn null (từ 3.1) nên banner không hiện ở chế độ khách hàng.

### File List

UPDATE:
- `frontend/src/App.tsx` (state showConflictDetail + banner tóm tắt/toggle, reset ở runQuery + handleClear)
- `frontend/src/App.css` (.conflict-body/.conflict-summary/.conflict-toggle/.conflict-detail)

## Change Log

- 2026-07-18: Story 3.2 — banner cảnh báo xung đột gọn + nút "Xem chi tiết" (aria-expanded). FE-only, không đụng backend. tsc/oxlint/build sạch, 41 test BE giữ nguyên. Status → review.
