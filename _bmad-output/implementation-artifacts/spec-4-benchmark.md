---
title: 'Epic 4 — Benchmark: baseline mode + màn 2 cột'
type: 'feature'
created: '2026-07-18'
status: 'done'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Chưa chứng minh được Compliance Copilot hơn RAG thường. Cần đặt cạnh nhau: cùng câu hỏi, baseline (RAG ngây thơ) trả sai/thiếu, hệ thống trả đúng + cảnh báo — màn chốt hạ khi pitch (FR-14, FR-15).

**Approach:** (4.1) Thêm chế độ `mode=baseline` tái dùng CÙNG pipeline nhưng TẮT lọc hiệu lực (temporal) + expand — baseline thấy cả bản cũ hết hiệu lực. (4.2) Màn Benchmark FE gọi `/api/chat` hai lần (baseline + system) cho cùng câu hỏi, hiện 2 cột và tô chỗ khác biệt.

## Boundaries & Constraints

**Always:** Baseline dùng CHUNG pipeline (AD-3), chỉ tắt stage temporal + expand — KHÔNG viết pipeline riêng. Lọc hiệu lực chỉ qua `is_active` (AD-5). Truy cập dữ liệu chỉ qua repository (AD-12). Contract `/api/chat` additive (AD-6) — `mode` đã có sẵn trong `ChatRequest`.

**Ask First:** Nếu cần đổi shape response `/api/chat` (thêm field mới) → HALT hỏi trước.

**Never:** KHÔNG làm baseline yếu giả tạo (NFR-6) — baseline vẫn retrieve + synthesize thật, chỉ bỏ temporal/expand. KHÔNG đụng benchmark bằng cách hardcode câu trả lời. KHÔNG phá chat/graph/conflict hiện có.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Baseline câu bẫy số | `mode=baseline`, "tỷ lệ an toàn vốn tối thiểu?" | sources CHỨA `TT41/Điều 6.3` (8%, hết hiệu lực) — vì không lọc temporal | N/A |
| System câu bẫy số | `mode=system` (mặc định), cùng câu | sources KHÔNG có `TT41/Điều 6.3`; có `TT22/Điều 1` (9%) + conflictWarning | N/A |
| Baseline bỏ dẫn chiếu | `mode=baseline`, câu về Điều 10 | KHÔNG kéo `TT41/Điều 6.3` qua REFERENCES (expand tắt) | N/A |
| Benchmark FE | Nhập câu ở màn Benchmark | 2 cột hiển thị đồng thời; cột khác biệt được tô | Lỗi 1 cột → hiện lỗi cột đó, cột kia vẫn chạy |

</frozen-after-approval>

## Code Map

- `backend/kb/repository_protocol.py` -- `search` thêm `apply_temporal`
- `backend/kb/repository.py` -- `search` bỏ lọc `is_active` khi `apply_temporal=False` (giữ lọc scope visibility)
- `backend/pipeline/retrieve.py` -- passthrough `apply_temporal`
- `backend/pipeline/query.py` -- `gather_candidates(mode)`: baseline = retrieve(no temporal), no expand
- `backend/api/main.py` -- nhánh `mode==baseline`: naive views (is_current=True, superseded_by=None), KHÔNG conflict, KHÔNG annotate
- `backend/tests/test_benchmark.py` -- NEW: baseline vs system
- `frontend/src/services/chatApi.ts` -- `mode` đã có trong `ChatOptions` (dùng lại)
- `frontend/src/components/BenchmarkPanel.tsx` -- NEW: 2 cột, gọi 2 lần, tô khác biệt
- `frontend/src/App.tsx`, `App.css` -- thêm tab "Benchmark"

## Tasks & Acceptance

**Execution:**
- [ ] `backend/kb/repository_protocol.py` + `repository.py` -- thêm `apply_temporal: bool = True` cho `search`; `False` → không lọc `is_active`, vẫn lọc scope -- baseline cần thấy bản hết hiệu lực
- [ ] `backend/pipeline/retrieve.py` -- nhận + truyền `apply_temporal` -- giữ AD-12
- [ ] `backend/pipeline/query.py` -- `gather_candidates(repo, q, as_of, scope, mode="system")`: `baseline` → `retrieve(apply_temporal=False)` + KHÔNG expand -- AD-3 tắt stage 2&3
- [ ] `backend/api/main.py` -- `mode=="baseline"`: build naive `CandidateView` (is_current=True, superseded_by=None), `conflictWarning=None`, KHÔNG annotate; else giữ nguyên -- NFR-6 baseline trung thực
- [ ] `backend/tests/test_benchmark.py` -- NEW: kiểm I/O Matrix (baseline có 6.3, system không; expand tắt)
- [ ] `frontend/src/components/BenchmarkPanel.tsx` -- NEW: input câu hỏi → gọi `sendChatRequest(q,{mode:'baseline'})` + `{mode:'system'}` song song; 2 cột "RAG thường" / "Compliance Copilot"; tô nguồn chỉ xuất hiện 1 bên
- [ ] `frontend/src/App.tsx` + `App.css` -- thêm tab "Benchmark"; style 2 cột

**Acceptance Criteria:**
- Given câu bẫy số + `mode=baseline`, when gọi `/api/chat`, then đáp án/nguồn phản ánh bản cũ 8% (retrieve không lọc temporal); `mode=system` phản ánh 9% + cảnh báo.
- Given màn Benchmark, when nhập 1 câu, then 2 cột hiện đồng thời cho cùng câu; ≥1 khác biệt được tô (bản cũ vs mới HOẶC thiếu dẫn chiếu — FR-15).
- Given 41 test cũ, when chạy pytest, then vẫn xanh (không phá).

## Design Notes

- `search(apply_temporal=False)`: bỏ điều kiện `is_active(c, as_of)` NHƯNG giữ `scope=="public"` visibility filter và token match. Baseline vẫn tôn trọng visibility (AD-11) — chỉ khác ở temporal.
- Naive views cho baseline: KHÔNG gọi `annotate` (annotate = trí tuệ temporal của hệ thống). Build thẳng `CandidateView(clause, is_current=True, superseded_by=None)` để synthesize thấy nguồn thô, không có gợi ý "đã thay thế".
- FR-15 (bằng chứng không cần delta số): câu về `TT41/Điều 10` (REFERENCES → 6.3) — system kéo được điều dẫn chiếu, baseline (expand tắt) thì không → khác biệt định tính.
- FE tô khác biệt: so `clauseId` giữa 2 danh sách nguồn; nguồn chỉ có ở 1 cột → thêm class nhấn (VD viền/nền nhạt).

## Verification

**Commands:**
- `cd backend && .venv/bin/python -m pytest -q` -- expected: 41 cũ + mới đều pass
- `cd frontend && npx tsc -b && npx oxlint && npm run build` -- expected: exit 0, build sạch

**Manual checks:**
- Mở tab Benchmark, hỏi "tỷ lệ an toàn vốn tối thiểu?" → cột trái (RAG thường) dính 8%/2 giá trị, cột phải (Copilot) 9% + cảnh báo; chỗ khác biệt được tô.
