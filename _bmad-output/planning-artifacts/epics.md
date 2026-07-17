---
stepsCompleted: [1]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-ibib-vic-2026-2026-07-17/prd.md
  - _bmad-output/planning-artifacts/architecture/architecture-ibib-vic-2026-2026-07-17/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/ux-designs/ux-ibib-vic-2026-2026-07-17/DESIGN.md
  - _bmad-output/planning-artifacts/ux-designs/ux-ibib-vic-2026-2026-07-17/EXPERIENCE.md
  - _bmad-output/planning-artifacts/briefs/brief-ibib-vic-2026-2026-07-17/addendum.md
---

# ibib-vic-2026 (Compliance Copilot) - Epic Breakdown

## Overview

Phân rã yêu cầu từ PRD, UX (DESIGN + EXPERIENCE) và Architecture Spine thành story chia được cho đội 6 người trong hackathon 48h. Mọi story bám bất biến kiến trúc (AD-1..AD-11) và token UX.

## Requirements Inventory

### Functional Requirements

- **FR-1:** Cắt văn bản theo cấu trúc Điều/Khoản/Điểm (không theo token cố định); mỗi chunk có `path` + `doc_code`.
- **FR-2:** Gắn quan hệ (AMENDS/SUPERSEDES/REFERENCES) + khoảng hiệu lực `[effective_date, expiry_date)` cho từng Clause; serialize đồ thị ra JSON `{documents,clauses,edges}`.
- **FR-3:** Nạp văn bản mới qua màn admin (đầy đủ: UI ingest; mức co: đọc file JSON sẵn).
- **FR-4:** Hỏi–đáp tiếng Việt qua `POST /api/chat`; request `{question, asOf?, mode?}`; lỗi trả mã đúng + `detail`; CORS.
- **FR-5:** Hybrid retrieve (MVP BM25) + expand dẫn chiếu 1–2 hop.
- **FR-6:** Trích nguồn tới cấp Điều/Khoản; mọi câu trả lời thành công đều có `sources[].clause_id`.
- **FR-7:** Chế độ chỉ-dữ-liệu-công-khai cho khách hàng (mọi source đều `public`).
- **FR-8:** Lọc theo hiệu lực (as-of); mặc định hôm nay; đầy đủ: chọn as-of quá khứ.
- **FR-9:** Loại đúng điều khoản bị thay thế một phần, nêu rõ khoản đã hết hiệu lực.
- **FR-10:** Dòng thời gian phiên bản điều khoản (duyệt SUPERSEDED_BY).
- **FR-11:** Quét & cảnh báo xung đột (rule quét thật ≥2 ca; `topic` để so khớp; đầy đủ: LLM judge).
- **FR-12:** Trực quan đồ thị tri thức (đầy đủ: tương tác; mức co: tĩnh).
- **FR-13:** Hiển thị trích nguồn & banner cảnh báo trong giao diện; bấm nguồn xem Điều/Khoản gốc.
- **FR-14:** Benchmark chạy đối chứng cạnh nhau (baseline = cùng pipeline, tắt expand+temporal).
- **FR-15:** Đa bằng chứng khác biệt (B: thay thế một phần, C: dẫn chiếu — không cần delta số; A: bẫy số nếu có).
- **FR-16 (STRETCH):** Radar báo cáo tác động khi nạp văn bản mới (deterministic, không hardcode).

### NonFunctional Requirements

- **NFR-1 (Hiệu năng):** P95 < 15 giây/câu ở demo; ingest chạy offline.
- **NFR-2 (Bảo mật):** API key LLM chỉ ở backend; CORS tới FE; luôn trả JSON.
- **NFR-3 (Độ tin cậy demo):** mock mode + bộ câu trả lời canned cho câu demo chính (fallback khi LLM lỗi/chậm).
- **NFR-4 (Ngôn ngữ):** nội dung và câu trả lời bằng tiếng Việt.
- **NFR-5 (Provenance):** mọi câu trả lời truy vết được về nguồn (đồng nhất FR-6).
- **NFR-6 (Trung thực dữ liệu):** amendment tổng hợp (nếu dùng) phải gắn nhãn kịch bản dựng; số nhất quán toàn mẫu.
- **NFR-7 (Không hardcode):** màn "chạy thật" (xung đột, Radar) để logic quét/duyệt dữ liệu thật.
- **NFR-8 (Chi phí):** gọi LLM API theo lượt, cân nhắc cache.

### Additional Requirements

*(Từ Architecture Spine — kỹ thuật, ràng buộc build)*

- **STARTER (tác động Epic 1 Story 1):** Frontend **dùng lại repo React+TS+Vite sẵn có** (KHÔNG init mới); backend/ đang trống — dựng skeleton FastAPI theo cây `api/pipeline/kb/providers/ingest`.
- **AD-1:** Commit `data/sample/corpus.schema.json` thật; mọi `edges.from/to = clause_id`; id sinh khi annotate tay.
- **AD-2:** KnowledgeBase bất biến, nạp 1 lần lúc startup; reload = dựng mới + atomic swap; request pin snapshot.
- **AD-3:** Pipeline stage cố định `retrieve→expand→temporal_filter→conflict_check→synthesize`; baseline = tắt expand+temporal qua `mode`; conflict chạy **sau** temporal.
- **AD-4:** `clause_id` ổn định dạng `"TT41/Điều 6.3"` là khóa mọi nơi.
- **AD-5:** một hàm `is_active(clause, asOf)`; `eff <= asOf AND (exp IS NULL OR asOf < exp)`.
- **AD-6:** contract `/api/chat` (request `{question,asOf,mode}`, `sources[]={clause_id,name,description}`, `conflictWarning?`); cập nhật `API_CONTRACT.md` (đã làm).
- **AD-7:** layering `api→pipeline→kb`; LLM sau provider interface; MVP **BM25-only**, embedding/vector store = Deferred.
- **AD-8:** secret + gọi model chỉ ở backend; FE chỉ gọi `/api/*`.
- **AD-9:** logic thật (conflict/radar) tách khỏi tầng fallback canned.
- **AD-10:** `Candidate.score` chuẩn hóa `[0,1]` (RRF khi thêm dense); ranking một chỗ ở `retrieve`.
- **AD-11:** lọc `visibility` ngay tại retrieve (chống rò nội bộ).
- **DEPLOY:** 3 tiến trình cục bộ — Vite:5173, FastAPI:8000, Streamlit:8501; seed corpus lúc startup (fail fast nếu thiếu); fallback demo qua `VITE_API_MODE=mock`.
- **STACK (pinned 7/2026):** Python 3.12, FastAPI 0.139.2, NetworkX 3.6.1, rank_bm25 0.2.2, httpx 0.28.1, React 19/TS~6/Vite 8, react-force-graph-2d 1.48.2, Streamlit 1.59.2, LLM Claude 4.6.

### UX Design Requirements

*(Từ DESIGN.md + EXPERIENCE.md — mỗi mục đủ cụ thể để sinh story)*

- **UX-DR1:** Design tokens CSS: brand SHB đỏ `#D81E28`/cam `#F58220` + màu ngữ nghĩa **tách khỏi brand** (active xanh, conflict amber, superseded xám, public, internal, danger).
- **UX-DR2:** Font Be Vietnam Pro (UI) + mono (JetBrains Mono) cho `clause_id`/số điều khoản.
- **UX-DR3:** Component **ChatBubble** (user phải / bot trái + khối nguồn dưới).
- **UX-DR4:** Component **SourceCard** — chip mono `clause_id`, tên VB, badge trạng thái, bấm → highlight node đồ thị (hai chiều).
- **UX-DR5:** Component **StatusBadge** (active/superseded/conflict/public/internal); "đã thay thế" kèm **gạch ngang**.
- **UX-DR6:** Component **ConflictBanner** (dải amber, icon ⚠, 2 nguồn, nút xem chi tiết).
- **UX-DR7:** **GraphPanel** — react-force-graph-2d từ JSON, cạnh màu theo loại quan hệ, bấm node → chi tiết + timeline.
- **UX-DR8:** **VersionTimeline** — trục các phiên bản theo SUPERSEDED_BY, bản cũ mờ + gạch ngang, bản hiện hành nổi bật.
- **UX-DR9:** **BenchmarkColumns** — 2 cột side-by-side đồng bộ cuộn, tô chỗ khác biệt.
- **UX-DR10:** **AsOfPicker** (→ `asOf`) + **ModeToggle** (→ `mode`, nhãn "Chế độ công khai" khi Khách hàng).
- **UX-DR11:** **AdminUpload** — kéo-thả/nhập, thanh tiến trình, nút "Chạy Radar".
- **UX-DR12:** 4 trạng thái mỗi bề mặt (loading/empty/error/success); empty gợi ý 3 câu mẫu (gồm 1 câu bẫy + 1 câu khách hàng).
- **UX-DR13:** Accessibility floor — tương phản AA, **trạng thái không chỉ bằng màu** (icon+chữ), điều hướng bàn phím, focus ring đỏ, ARIA, bảng thay thế cho đồ thị.
- **UX-DR14:** Microcopy tiếng Việt (placeholder ô hỏi, cảnh báo thay thế/xung đột, thông báo fallback).
- **UX-DR15:** Layout desktop-first 2 cột (chat + panel thu/mở với tab Đồ thị/Timeline); màn Benchmark riêng; màn Admin riêng.
- **UX-DR16:** Mockup tham chiếu màn Trợ lý: `ux-designs/.../mockups/mock-troly.html` (spine thắng nếu lệch).

### FR Coverage Map

{{requirements_coverage_map}}

## Epic List

{{epics_list}}
