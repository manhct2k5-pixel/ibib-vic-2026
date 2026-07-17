---
baseline_commit: f12c67d723f79a905aad1904d0d41343906bb622
---

# Story 1.6: Giao diện chat + nguồn + AsOfPicker + fallback

Status: review

<!-- Ultimate context engine analysis completed - comprehensive developer guide created -->

## Story

As a nhân viên,
I want khung chat hiển thị câu trả lời, nguồn bấm được với trạng thái hiệu lực, chọn mốc thời gian, và không trắng màn khi lỗi,
so that trải nghiệm tra cứu rõ ràng, đáng tin, đúng bản sắc — thay cho starter chung chung.

## Acceptance Criteria

1. **Đổi bản sắc + design tokens (UX-DR1,2,15).** `App.css :root` khai CSS variables theo `DESIGN.md`: brand SHB đỏ `#D81E28`/cam `#F58220`; màu ngữ nghĩa TÁCH brand (active `#16A34A`, conflict `#D97706`, superseded `#94A3B8`, public/internal, danger); font `Be Vietnam Pro` (UI) + mono cho `clause_id`. Tiêu đề đổi thành "Trợ lý tra cứu văn bản ngân hàng thông minh".
2. **SourceCard trạng thái (UX-DR4,5).** Mỗi nguồn hiển thị: **chip mono `clause_id`**, tên văn bản, mô tả, và **StatusBadge**: "Hiệu lực" (xanh) nếu `isCurrent`, hoặc "Đã thay thế" (xám + **gạch ngang** mô tả + ghi "bởi {supersededBy}") nếu không. Không chỉ dùng màu — kèm chữ/icon (a11y, UX-DR13).
3. **AsOfPicker (UX-DR10).** Có ô chọn ngày (mặc định hôm nay); đổi ngày → gửi lại truy vấn với `asOf` tương ứng qua `sendChatRequest(question, {asOf})`.
4. **Banner cảnh báo (UX-DR6, slot).** Nếu response có `conflictWarning` khác null → hiện dải amber phía trên câu trả lời. (Nội dung xung đột thật là Epic 3; story này chỉ hiển thị nếu có.)
5. **4 trạng thái + gợi ý (UX-DR12).** loading (spinner) / empty (gợi ý **3 câu mẫu** bấm được, gồm 1 câu "bẫy thời gian" + 1 câu khách hàng) / error (thông báo, không trắng màn) / success.
6. **Fallback demo (NFR-3, AD-9).** `VITE_API_MODE=mock` vẫn chạy (đã có). Ghi chú/nhãn nhỏ khi đang ở chế độ mock.
7. **FE đọc trường mới (nợ từ code-review).** `chatApi.ts` `SourceItem` thêm `isCurrent`/`supersededBy`; `parseSources` đọc chúng; key React dùng `clauseId` (không phải `name`).

## Tasks / Subtasks

- [x]**Task 1 — chatApi.ts đọc trạng thái** (AC: 7)
  - [x]UPDATE `frontend/src/services/chatApi.ts`: `SourceItem` thêm `isCurrent: boolean` + `supersededBy: string | null`; `parseSources` đọc `is_current`/`superseded_by` từ payload (mặc định true/null); mock response thêm 2 trường
- [x]**Task 2 — Design tokens + bản sắc** (AC: 1)
  - [x]UPDATE `frontend/src/App.css`: `:root` CSS variables theo DESIGN.md (brand + semantic + spacing + rounded); import/khai font Be Vietnam Pro + mono; đổi tiêu đề/nhãn
  - [x]`frontend/index.html`: thêm link font (Be Vietnam Pro) nếu dùng Google Fonts
- [x]**Task 3 — SourceCard + StatusBadge** (AC: 2)
  - [x]NEW `frontend/src/components/SourceCard.tsx`: chip mono clause_id + tên + mô tả + StatusBadge; superseded → gạch ngang + badge "Đã thay thế bởi {supersededBy}"
  - [x]UPDATE `App.tsx`: render `SourceCard` cho mỗi nguồn, key = `source.clauseId`
- [x]**Task 4 — AsOfPicker + banner + trạng thái** (AC: 3, 4, 5, 6)
  - [x]NEW `frontend/src/components/AsOfPicker.tsx` (hoặc inline): `<input type="date">` mặc định hôm nay
  - [x]UPDATE `App.tsx`: giữ state `asOf`; `sendChatRequest(question, { asOf })`; đổi ngày gọi lại
  - [x]Empty state: 3 câu mẫu bấm được (điền vào ô hỏi): "Tỷ lệ an toàn vốn tối thiểu hiện nay?", "Quy định X năm 2019 là gì?", "(khách hàng) ..."; banner conflictWarning; nhãn mock mode
- [x]**Task 5 — Kiểm tra** (AC tất cả)
  - [x]`npx tsc -b` sạch; `npx oxlint` sạch; chạy `npm run dev` xem thử ở cả mock và real

## Dev Notes

### Bối cảnh (đọc kỹ)
- ✅ `frontend/src/App.tsx` HIỆN là **starter chung** ("Trợ lý AI", "khung dùng chung") — story này **đổi thành sản phẩm thật**. Giữ cấu trúc state (question/answer/error/isLoading/sources) + xử lý submit/timeout; **thêm** `asOf`, `conflictWarning`, render SourceCard.
- ✅ `frontend/src/services/chatApi.ts` (Story 1.1/1.4): `sendChatRequest(question, options?: {asOf, mode})` đã hỗ trợ `asOf`. `SourceItem` có `clauseId` nhưng **CHƯA** có `isCurrent`/`supersededBy` — backend Story 1.4 đã trả 2 trường này (`isCurrent`, `supersededBy`), FE cần đọc.
- ✅ Backend response: `{answer, sources:[{clause_id,name,description,isCurrent,supersededBy}], conflictWarning}`.
- ✅ `App.css` hiện có class `.topbar/.result-card/.source-item/...` — refactor theo token, đừng giữ tên "Trợ lý AI".
- ✅ UX spines: `DESIGN.md` (tokens, component specs) + `EXPERIENCE.md` (hành vi, microcopy) + mock `ux-designs/.../mockups/mock-troly.html` (tham chiếu bố cục màn Trợ lý).

### Nguồn thiết kế (bám sát)
- [Source: _bmad-output/planning-artifacts/ux-designs/ux-ibib-vic-2026-2026-07-17/DESIGN.md] — tokens, SourceCard, StatusBadge, ConflictBanner specs.
- [Source: .../EXPERIENCE.md] — microcopy ("⚠ Điều khoản cũ đã bị thay thế..."), state patterns, KF-1.
- [Source: .../mockups/mock-troly.html] — bố cục tham chiếu (chip mono đỏ, badge, gạch ngang).

### Guardrail
- **AD-6:** không đổi contract; chỉ đọc thêm field additive đã có.
- **AD-8:** FE không chứa key, chỉ gọi `/api/*` (giữ nguyên).
- **UX-DR13 a11y:** trạng thái không chỉ bằng màu — kèm chữ ("Đã thay thế") + gạch ngang; focus ring; nhãn ARIA.
- **Phạm vi — KHÔNG làm quá:** KHÔNG dựng GraphPanel/VersionTimeline (Epic 2); KHÔNG ModeToggle khách hàng (Story 1.7); KHÔNG canned answers phức tạp (chỉ giữ mock mode sẵn có). Panel bên phải (đồ thị/timeline) để chỗ trống/placeholder cho Epic 2.

### File sẽ chạm
| File | NEW/UPDATE |
|---|---|
| `frontend/src/services/chatApi.ts` | UPDATE (isCurrent/supersededBy) |
| `frontend/src/App.tsx` | UPDATE (rebrand, SourceCard, AsOfPicker, states, banner) |
| `frontend/src/App.css` | UPDATE (tokens + component styles) |
| `frontend/src/components/SourceCard.tsx` | NEW |
| `frontend/src/components/AsOfPicker.tsx` | NEW (hoặc inline trong App.tsx) |
| `frontend/index.html` | UPDATE (font link) |

### Testing standards
- FE chưa có test runner (chỉ tsc + oxlint). Bắt buộc: `npx tsc -b` exit 0, `npx oxlint` exit 0. Kiểm thủ công `npm run dev`.
- KHÔNG cần thêm test framework cho story này (giữ nhẹ cho hackathon).

### References
- [Source: epics.md#Story 1.6 (FR-13) + UX-DR1,2,3,4,5,10,12,13,14,15]
- [Source: ARCHITECTURE-SPINE.md#AD-6,AD-8]
- [Source: backend/api/main.py (response shape), frontend/src/App.tsx, App.css, chatApi.ts]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (cc/claude-opus-4-8) — bmad-dev-story

### Debug Log References

- `tsc -b`: exit 0 · `oxlint src/`: exit 0 · `vite build`: exit 0 (194 kB JS / 4.35 kB CSS).

### Completion Notes List

- **Đổi bản sắc + tokens:** `App.css` viết lại với CSS variables SHB đỏ-cam + màu ngữ nghĩa tách brand + font Be Vietnam Pro/JetBrains Mono; `index.html` link Google Fonts + title. Tiêu đề "Trợ lý tra cứu văn bản ngân hàng · SHB".
- **SourceCard:** chip mono `clause_id` + StatusBadge (Hiệu lực xanh / Đã thay thế xám + "bởi {supersededBy}") + mô tả gạch ngang khi đã thay thế. Trạng thái kèm chữ, không chỉ màu (a11y).
- **AsOfPicker:** `<input type="date">` mặc định hôm nay; đổi ngày → tự gửi lại truy vấn cuối (time-travel).
- **conflictWarning banner** (amber) hiển thị khi có; **4 trạng thái** (loading/empty/error/success); empty có **3 câu mẫu bấm được**; nhãn "Chế độ mock" khi `VITE_API_MODE=mock`.
- **chatApi.ts:** `SourceItem` thêm `isCurrent`/`supersededBy`; `parseSources` đọc chúng; key React đổi sang `clauseId` (trả nợ code-review). Mock response cập nhật.
- Phạm vi giữ đúng: KHÔNG GraphPanel/Timeline (Epic 2), KHÔNG ModeToggle khách hàng (Story 1.7).

### File List

NEW:
- `frontend/src/components/SourceCard.tsx`

UPDATE:
- `frontend/src/services/chatApi.ts` (isCurrent/supersededBy)
- `frontend/src/App.tsx` (rebrand, AsOfPicker, SourceCard, banner, states, samples)
- `frontend/src/App.css` (design tokens + component styles)
- `frontend/index.html` (font link + title)

## Change Log

- 2026-07-17: Story 1.6 — giao diện Compliance Copilot: tokens SHB, SourceCard trạng thái hiệu lực, AsOfPicker time-travel, banner xung đột, 4 trạng thái + gợi ý. tsc/oxlint/build sạch. Status → review.
- 2026-07-18: Code-review fixes — chuẩn hóa snake_case `is_current`/`superseded_by` (BE+FE+test); **race guard** cho AsOfPicker (chỉ nhận response mới nhất) + disable input khi loading; render khi answer rỗng nhưng có nguồn; reset lastQuestion khi Xóa; câu mẫu bẫy-thời-gian + khách hàng (AC5); focus ring đỏ; `lang="vi"`; TODAY theo giờ địa phương; word-break desc. 25 test BE pass, tsc/oxlint/build sạch. Status → done.
