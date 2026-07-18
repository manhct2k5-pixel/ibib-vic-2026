---
baseline_commit: 1c491229811d277a45b6a292607d206410ce946d
---

# Story 2.1: Trực quan đồ thị tri thức

Status: review

<!-- Ultimate context engine analysis completed - comprehensive developer guide created -->

## Story

As a người dùng,
I want thấy các văn bản và quan hệ (sửa đổi / thay thế / dẫn chiếu) dưới dạng **đồ thị tương tác**,
so that tôi hiểu được cấu trúc chồng chéo giữa các quy định thay vì chỉ đọc danh sách.

## Acceptance Criteria

1. **Backend expose đồ thị.** Có endpoint `GET /api/graph` trả `repository.export_graph()` = `{nodes:[...], edges:[...]}` (FR-12). Nhận `?audience=employee|customer` → suy `scope`; **customer chỉ thấy node/edge public** (đóng cái defer từ code-review 1.7 — `export_graph` phải nhận scope).
2. **Đồ thị tương tác FE.** Panel "Đồ thị tri thức" render `react-force-graph-2d` từ JSON: node = điều khoản, cạnh màu theo loại quan hệ (SUPERSEDES/AMENDS/REFERENCES/GUIDES). Node đã hết hiệu lực hiển thị khác (xám) node còn hiệu lực.
3. **Bấm node xem chi tiết.** Bấm một node → hiện `clause_id`, `path`, trạng thái hiệu lực (kèm nút/hook mở timeline ở Story 2.2 — story này chỉ cần chỗ hiển thị chi tiết).
4. **A11y — bảng thay thế (UX-DR13).** Có danh sách quan hệ dạng bảng/list cho người không thao tác đồ hình (VD "TT22/Điều 1 —SUPERSEDES→ TT41/Điều 6.3").
5. **Bố trí panel.** Đồ thị nằm ở panel bên (chỗ placeholder Story 1.6 để trống) hoặc một tab riêng; không phá màn chat.

## Tasks / Subtasks

- [x] **Task 1 — Endpoint /api/graph (AC: 1)**
  - [x] UPDATE `kb/repository_protocol.py` + `kb/repository.py`: `export_graph(scope="all")` — khi `scope="public"` bỏ node `internal` và edge chạm node internal
  - [x] UPDATE `api/main.py`: `GET /api/graph` (query `audience`) → `export_graph(scope)`; giữ contract JSON `{nodes, edges}`
  - [x] Test: `export_graph(scope="public")` không có `QD-INT/Điều 2`; endpoint trả 200 + shape đúng
- [x] **Task 2 — Cài lib + service FE (AC: 2)**
  - [x] `npm install react-force-graph-2d` (frontend)
  - [x] NEW `frontend/src/services/graphApi.ts`: `fetchGraph(audience)` → `{nodes, edges}` (type rõ)
- [x] **Task 3 — Component GraphPanel (AC: 2, 3, 4)**
  - [x] NEW `frontend/src/components/GraphPanel.tsx`: nạp graph, render `<ForceGraph2D>`; màu cạnh theo `type`; node xám nếu `expiry_date` đã qua; bấm node → state `selected` hiển thị chi tiết; danh sách quan hệ (bảng a11y)
  - [x] UPDATE `App.tsx`: thêm panel/tab "Đồ thị tri thức"; truyền `audience` hiện tại
  - [x] UPDATE `App.css`: khung panel + màu cạnh (dùng token semantic)
- [x] **Task 4 — Kiểm tra**
  - [x] Backend: pytest giữ 29 test cũ + test mới export_graph scope (35 passed)
  - [x] Frontend: `tsc -b` + `oxlint` + `vite build` sạch

## Dev Notes

### Bối cảnh (tái dùng — Epic 1 đã có sẵn)
- ✅ `repository.export_graph()` ĐÃ có (Story 1.2) trả `{nodes, edges}` với node có `id, doc_code, path, topic, visibility, expiry_date`. **CHƯA nhận scope** → story này thêm (đóng defer 1.7).
- ✅ `api/main.py`: đã có `create_app` + CORS + `/api/chat` + `/health`. Thêm route `GET /api/graph`.
- ✅ `chatApi.ts` có pattern gọi API (mock/real, base URL). `graphApi.ts` theo cùng kiểu (nhưng graph chỉ chế độ real; mock có thể trả graph rỗng hoặc bỏ qua).
- ✅ `App.tsx` (Story 1.6/1.7): layout 1 cột chat + `audience` state + ModeToggle. Panel đồ thị nằm cạnh/tab.
- ✅ Token màu trong `App.css`: cạnh theo loại quan hệ dùng `--brand-red`/`--brand-orange`/`--muted`; node superseded dùng `--superseded`.
- ✅ 29 test BE + FE build xanh — giữ nguyên.

### Thư viện: react-force-graph-2d
- Dùng `<ForceGraph2D graphData={{nodes, links}} />`. **Lưu ý:** lib dùng khóa `links` (không phải `edges`), và mỗi link cần `source`/`target` (không phải `from`/`to`). → `graphApi`/`GraphPanel` map: `edges[].from→source`, `to→target`, giữ `type`.
- Node cần `id`. Backend đã trả `id`.
- Màu: `nodeColor` theo `expiry_date` (null/tương lai = active xanh, đã qua = xám); `linkColor` theo `type`.
- Xác thực phiên bản mới nhất khi cài (react-force-graph-2d ~1.48.x theo Stack spine).

### Guardrail
- **AD-1/AD-12:** graph lấy TỪ `repository.export_graph()` — không tự query/parse; đóng gói trong repository.
- **AD-11 (đóng defer):** `export_graph` phải lọc theo scope khi customer.
- **AD-6:** endpoint mới, không phá `/api/chat`.
- **Phạm vi — KHÔNG làm quá:** timeline phiên bản là **Story 2.2**; bấm-nguồn↔highlight-node là **Story 2.3**. Story này chỉ: đồ thị + bấm node xem chi tiết cơ bản.
- [Source: ARCHITECTURE-SPINE.md#AD-1,AD-11,AD-12; epics.md#Story 2.1 (FR-12, UX-DR7); DESIGN.md/EXPERIENCE.md GraphPanel]

### File sẽ chạm
| File | NEW/UPDATE |
|---|---|
| `backend/kb/repository_protocol.py`, `repository.py` | UPDATE (export_graph scope) |
| `backend/api/main.py` | UPDATE (GET /api/graph) |
| `backend/tests/test_graph.py` | NEW |
| `frontend/package.json` | UPDATE (react-force-graph-2d) |
| `frontend/src/services/graphApi.ts` | NEW |
| `frontend/src/components/GraphPanel.tsx` | NEW |
| `frontend/src/App.tsx`, `App.css` | UPDATE (panel/tab) |

### Dữ liệu (corpus.json)
7 clause, các cạnh: `TT22/Điều 1 SUPERSEDES TT41/Điều 6.3`, `TT22/Điều 2 SUPERSEDES TT41/Điều 8.2`, `TT41/Điều 10 REFERENCES TT41/Điều 6.3`. `QD-INT/Điều 2` internal (kiểm scope).

### Testing standards
- Backend pytest (giữ 29 + mới). Frontend tsc/oxlint/build. Kiểm thủ công `npm run dev`.

### References
- [Source: epics.md#Story 2.1; ARCHITECTURE-SPINE.md#AD-1,AD-11,AD-12]
- [Source: backend/kb/repository.py (export_graph), backend/api/main.py; frontend/src/App.tsx, chatApi.ts]
- [Source: ux-designs/.../DESIGN.md (GraphPanel), EXPERIENCE.md (a11y bảng thay thế)]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (cc/claude-opus-4-8) — bmad-dev-story

### Debug Log References

- Backend `pytest`: **35 passed** (29 cũ + 6 mới `test_graph.py`), 0.29s.
- Frontend: `tsc -b` exit 0 · `oxlint` exit 0 · `vite build` sạch (1047 modules, gzip JS 125KB — gồm react-force-graph-2d).
- Lib cài được: `react-force-graph-2d@1.29.1` (bản npm resolve; đủ API `<ForceGraph2D>` cần dùng).

### Completion Notes List

- **Task 1 — Endpoint đồ thị + scope (đóng defer 1.7):** `export_graph(scope="all")` thêm vào Protocol + `StubRepository`; `scope="public"` lọc bỏ node `visibility!="public"` VÀ mọi edge chạm node đã bị loại (không rò internal qua cạnh — AD-11). Endpoint `GET /api/graph?audience=…` suy `scope` fail-closed (chỉ `employee` chính xác mới thấy internal), giữ contract JSON `{nodes, edges}`. Bổ sung mục §4b trong `API_CONTRACT.md`.
- **Task 2 — Service FE:** `graphApi.ts` gọi `GET /api/graph`, parse an toàn, và **map khóa cho react-force-graph-2d**: `edges[].from→source`, `to→target`, giữ `type`; trả `{nodes, links}` (lib dùng `links`, không phải `edges`).
- **Task 3 — GraphPanel:** `<ForceGraph2D>` với `nodeColor` (xanh còn hiệu lực / xám hết hiệu lực theo `expiry_date` so với hôm nay), `linkColor` theo `type` (SUPERSEDES đỏ / AMENDS cam / REFERENCES xám / GUIDES xanh dương), mũi tên hướng. Bấm node → panel chi tiết (`clause_id`, path, topic, trạng thái) + nút "Xem dòng thời gian (2.2)" disabled (hook cho Story 2.2). Bảng "Danh sách quan hệ" (a11y UX-DR13) liệt kê Nguồn—Quan hệ→Đích. Clone link trước khi đưa vào canvas để ForceGraph không mutate dữ liệu bảng. Đo bề rộng container để canvas không tràn.
- **App.tsx:** thêm thanh tab "Trò chuyện / Đồ thị tri thức" (role=tablist), không phá màn chat; GraphPanel nhận `audience` hiện tại (đổi Nhân viên/Khách hàng → nạp lại đồ thị đúng scope).
- **Phạm vi giữ đúng:** KHÔNG làm timeline phiên bản (Story 2.2), KHÔNG bấm-nguồn↔highlight-node (Story 2.3). Chỉ đồ thị + bấm node xem chi tiết + bảng a11y.

### File List

NEW:
- `backend/tests/test_graph.py`
- `frontend/src/services/graphApi.ts`
- `frontend/src/components/GraphPanel.tsx`

UPDATE:
- `backend/kb/repository_protocol.py` (export_graph nhận scope)
- `backend/kb/repository.py` (export_graph lọc node/edge theo scope)
- `backend/api/main.py` (GET /api/graph → export_graph(scope))
- `frontend/src/App.tsx` (tab Trò chuyện/Đồ thị, render GraphPanel)
- `frontend/src/App.css` (tab-bar, graph-panel, legend, canvas, node-detail, bảng quan hệ)
- `frontend/package.json` + `package-lock.json` (react-force-graph-2d)
- `docs/architecture/API_CONTRACT.md` (§4b GET /api/graph)

## Change Log

- 2026-07-18: Story 2.1 — trực quan đồ thị tri thức. BE: `export_graph(scope)` + endpoint `GET /api/graph` (đóng defer 1.7, lọc internal khi customer). FE: cài react-force-graph-2d, `graphApi.ts` (map from/to→source/target), `GraphPanel.tsx` (đồ thị màu theo hiệu lực/quan hệ, bấm node chi tiết, bảng a11y), tab Trò chuyện/Đồ thị trong App. 35 test BE pass, FE tsc/oxlint/build sạch. Status → review.
