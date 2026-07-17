---
stepsCompleted: [1, 2, 3, 4]
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
- **FR-5:** Retrieve (MVP Postgres full-text) + expand dẫn chiếu 1–2 hop.
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
- **AD-7:** layering `api→pipeline→repository→PostgreSQL`; LLM sau provider interface; tìm kiếm bằng Postgres full-text, embedding/vector store = Deferred.
- **AD-12:** truy cập DB chỉ qua `kb/repository.py`; pipeline/api không viết SQL. Hợp đồng `Clause`/`ConflictPair` dataclass (do Epic 0 giao ra).
- **AD-8:** secret + gọi model chỉ ở backend; FE chỉ gọi `/api/*`.
- **AD-9:** logic thật (conflict/radar) tách khỏi tầng fallback canned.
- **AD-10:** `Candidate.score` chuẩn hóa `[0,1]` (RRF khi thêm dense); ranking một chỗ ở `retrieve`.
- **AD-11:** lọc `visibility` ngay tại retrieve (chống rò nội bộ).
- **DEPLOY:** 3 tiến trình cục bộ — Vite:5173, FastAPI:8000, Streamlit:8501; seed corpus lúc startup (fail fast nếu thiếu); fallback demo qua `VITE_API_MODE=mock`.
- **STACK (pinned 7/2026):** Python 3.12, **PostgreSQL 17 + psycopg 3**, FastAPI 0.139.2, httpx 0.28.1, React 19/TS~6/Vite 8, react-force-graph-2d 1.48.2, Streamlit 1.59.2, LLM Claude 4.6. *(Bỏ NetworkX/rank_bm25 — Postgres lo quan hệ + full-text.)*

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

- **FR-1** → Epic 1 (cắt văn bản theo Điều/Khoản)
- **FR-2** → Epic 1 (gắn quan hệ + hiệu lực; JSON đồ thị)
- **FR-3** → Epic 1 (mức co: đọc JSON lúc startup) + Epic 5 (UI ingest đầy đủ)
- **FR-4** → Epic 1 (`/api/chat`)
- **FR-5** → Epic 1 (retrieve Postgres full-text + expand dẫn chiếu)
- **FR-6** → Epic 1 (trích nguồn tới Điều/Khoản)
- **FR-7** → Epic 1 (chế độ công khai — lọc visibility)
- **FR-8** → Epic 1 (lọc as-of)
- **FR-9** → Epic 1 (thay thế một phần)
- **FR-10** → Epic 2 (dòng thời gian phiên bản)
- **FR-11** → Epic 3 (phát hiện xung đột)
- **FR-12** → Epic 2 (trực quan đồ thị)
- **FR-13** → Epic 1 (hiển thị nguồn) + Epic 2 (bấm nguồn→node) + Epic 3 (banner xung đột)
- **FR-14** → Epic 4 (benchmark side-by-side)
- **FR-15** → Epic 4 (đa bằng chứng B/C)
- **FR-16** → Epic 6 (Radar — stretch)

## Epic List

> **Thứ tự chạm (lộ trình 48h, khác số thứ tự epic — đồng thuận party):** dựng **lát cắt xuyên** đầu tiên = đường ống xanh (E1 tối thiểu) + **một cặp benchmark** (E4 tối thiểu) để chứng minh khác biệt sớm và làm test tích hợp sống → rồi bơm đầy E1 → E2 → E3 → E5 → E6 (stretch). Story 1.1 khóa **corpus schema + contract** trước khi ai đụng phím; data do 1 người giỏi nghiệp vụ sở hữu từ H0.

> **Phân chia người:** **Epic 0 (Database)** do **một người khác** phụ trách — dựng Postgres + dữ liệu + lớp truy vấn. Phần còn lại (Epic 1–6) do bạn phụ trách, **tiêu thụ interface repository của Epic 0**, không chạm SQL. Ranh giới bàn giao = `backend/kb/repository.py` (xem "Ranh giới bàn giao" cuối phần Epic 0).

### Epic 0: Nền tảng Dữ liệu & Database *(người khác phụ trách — tiên quyết)*
Cung cấp lớp dữ liệu hoàn chỉnh: PostgreSQL + corpus đã chuẩn hóa + interface truy vấn (`repository.py`), để Epic 1–6 tiêu thụ mà không viết SQL. Logic thời gian/xung đột/tìm kiếm nằm trong lớp này (SQL).
**FRs covered (phần dữ liệu):** FR-1, FR-2 (chuẩn hóa Điều/Khoản + quan hệ vào DB); hỗ trợ truy vấn cho FR-5, FR-8, FR-9, FR-10, FR-11, FR-12.

### Epic 1: Hỏi–đáp đúng-thời-điểm có trích nguồn *(CORE + nền tảng — phần của bạn)*
Nhân viên hỏi tiếng Việt và nhận câu trả lời theo **bản còn hiệu lực**, kèm **trích nguồn** tới cấp Điều/Khoản; hỗ trợ chế độ khách hàng (chỉ dữ liệu công khai). Bao gồm nền tảng: dùng lại repo React, dựng skeleton FastAPI, nạp corpus + KnowledgeBase, wire `/api/chat`, fallback demo.
**FRs covered:** FR-1, FR-2, FR-4, FR-5, FR-6, FR-7, FR-8, FR-9, FR-13 (hiển thị nguồn), FR-3 (mức co: đọc JSON)

### Epic 2: Thấy quan hệ & lịch sử điều khoản
Người dùng xem **đồ thị tri thức** và **dòng thời gian phiên bản** của một điều khoản; bấm nguồn → highlight node (hai chiều).
**FRs covered:** FR-10, FR-12, FR-13 (bấm nguồn→node)

### Epic 3: Cảnh báo xung đột
Người dùng được cảnh báo khi hai quy định cùng hiệu lực mâu thuẫn số liệu (rule quét thật ≥2 ca).
**FRs covered:** FR-11, FR-13 (banner xung đột)

### Epic 4: Chứng minh hơn RAG thường (Benchmark)
Đặt hệ thống cạnh RAG baseline trên cùng dữ liệu, **đa bằng chứng** (A/B/C) — màn chốt hạ khi pitch.
**FRs covered:** FR-14, FR-15

### Epic 5: Quản trị nội dung (Admin/Ingest)
Admin nạp văn bản mới qua UI mà không cần chạm code; cập nhật đồ thị qua atomic swap.
**FRs covered:** FR-3 (đầy đủ — UI ingest)

### Epic 6 (STRETCH): Radar Tác động
Khi nạp văn bản sửa đổi, hệ thống báo cáo điều khoản/văn bản bị ảnh hưởng. Chỉ làm sau khi Epic 1–5 chạy ổn. Phụ thuộc Epic 5 (ingest) + Epic 2 (đồ thị).
**FRs covered:** FR-16

---

## Epic 0: Nền tảng Dữ liệu & Database *(người khác phụ trách)*

Mục tiêu: giao ra một **lớp dữ liệu chạy được** — Postgres + corpus + `repository.py` — để Epic 1–6 gọi hàm, không viết SQL. Tài sản có sẵn: `backend/db/schema.sql`, `backend/db/docker-compose.yml`, `data/sample/corpus.json` + `corpus.schema.json`.

### Story 0.1: Dựng PostgreSQL + schema
As a người phụ trách database,
I want một Postgres chạy được với 3 bảng documents/clauses/edges,
so that có nơi lưu bền vững cho dữ liệu pháp lý.

**Acceptance Criteria:**

**Given** `backend/db/docker-compose.yml` và `schema.sql`,
**When** chạy `docker compose up -d`,
**Then** Postgres 17 lên ở cổng 5432, 3 bảng + index + extension `unaccent` được tạo tự động.
**And** kết nối được bằng `postgresql://ibib:ibib@localhost:5432/compliance`.

### Story 0.2: Chuẩn bị & mở rộng corpus
As a người phụ trách database,
I want corpus đã chuẩn hóa đủ các ca demo,
so that mọi tính năng phía sau có dữ liệu thật để chạy.

**Acceptance Criteria:**

**Given** `corpus.json` mẫu,
**When** hoàn thiện dữ liệu,
**Then** có đủ **3 hạt giống** (bẫy số 8%→9%, thay thế một phần, dẫn chiếu) + **≥1 ca xung đột** + nhãn `public/internal` (FR-1, FR-2).
**And** file validate hợp lệ với `corpus.schema.json`; nếu dùng dữ liệu dựng thì `_meta.synthetic=true` (NFR-6).

### Story 0.3: Seed loader (corpus.json → Postgres)
As a người phụ trách database,
I want một script nạp corpus vào Postgres,
so that dữ liệu vào DB lặp lại được, không thủ công.

**Acceptance Criteria:**

**Given** Postgres đang chạy và `corpus.json` hợp lệ,
**When** chạy `python backend/ingest/seed_db.py`,
**Then** documents/clauses/edges được INSERT đúng; chạy lại **không nhân đôi** (idempotent, upsert theo khóa).
**And** báo số bản ghi đã nạp; lỗi tham chiếu (edge trỏ clause không tồn tại) → dừng + log rõ.

### Story 0.4: Lớp Repository (interface — RANH GIỚI BÀN GIAO)
As a người phụ trách database,
I want một module `repository.py` gói mọi truy vấn SQL sau interface hàm,
so that phần còn lại của đội gọi hàm mà không cần biết SQL.

**Acceptance Criteria:**

**Given** dữ liệu đã ở Postgres,
**When** cung cấp `backend/kb/repository.py`,
**Then** có các hàm (trả về object Python, không phải SQL thô):
- `search(q: str, as_of: date, mode: str) -> list[Clause]` — full-text + **lọc hiệu lực** + lọc `visibility` nếu mode=public (FR-5, FR-8, FR-9, AD-11)
- `expand_references(clause_ids) -> list[Clause]` (FR-5)
- `find_conflicts(as_of) -> list[ConflictPair]` — cùng topic, cùng hiệu lực, khác `metric_value` (FR-11)
- `version_timeline(clause_id) -> list[Clause]` — chuỗi SUPERSEDES (FR-10)
- `export_graph() -> dict` — `{nodes, edges}` cho trực quan (FR-12)
- `insert_document(...)` — cho Admin ingest (FR-3, Epic 5)
**And** mỗi hàm có docstring + kiểu trả về rõ; có ≥1 test cho `search` (ca 8% bị loại, 9% giữ) và `find_conflicts`.
**And** `Clause`/`ConflictPair` là dataclass ổn định (khóa `clause_id`) — hợp đồng dữ liệu cho Epic 1+.

### Ranh giới bàn giao (seam) — Epic 0 ↔ phần của bạn
- **Người DB giao ra:** Postgres chạy + `repository.py` với các hàm trên + `Clause`/`ConflictPair` dataclass.
- **Bạn nhận vào:** chỉ `import` và gọi hàm `repository`. **Không viết SQL, không truy vấn DB trực tiếp.** Pipeline của bạn (retrieve→expand→temporal→conflict→synthesize) trở thành *điều phối* các hàm repository + gọi LLM.
- **Chốt sớm hợp đồng:** kiểu `Clause` (các field: `clause_id, doc_code, path, body, effective_date, expiry_date, topic, visibility, metric_value`) phải khóa ở Story 0.4 trước khi bạn code Epic 1 pipeline — để hai phía không lệch.
- **Bạn KHÔNG bị chặn hoàn toàn:** Story 1.1 (đường ống xanh, contract, FE wire) làm song song với Epic 0 bằng repository **giả (stub)** trả dữ liệu cứng; khi Epic 0.4 xong thì thay stub bằng repository thật.

## Epic 1: Hỏi–đáp đúng-thời-điểm có trích nguồn *(phần của bạn)*

Mục tiêu: nhân viên hỏi tiếng Việt và nhận câu trả lời theo bản còn hiệu lực, kèm trích nguồn; hỗ trợ chế độ khách hàng. Gồm nền tảng chạy end-to-end. **Tiêu thụ `repository` của Epic 0** (không tự dựng KnowledgeBase in-memory nữa).

### Story 1.1: Đường ống xanh (skeleton + contract + corpus)
As a lập trình viên trong đội,
I want một đường ống end-to-end (FE → `/api/chat` → BE trả lời giả) cùng corpus schema và contract đã khóa,
So that cả 6 người có mặt bằng chung để làm song song ngay từ H0.

**Acceptance Criteria:**

**Given** repo React sẵn có và `backend/` trống,
**When** dựng skeleton FastAPI (`api/pipeline/kb/providers/ingest`) và chạy,
**Then** `POST /api/chat` trả `{answer, sources[]}` (giả) đúng `API_CONTRACT.md`, có header CORS cho `http://localhost:5173`.
**And** frontend ở `VITE_API_MODE=real` gọi được và hiển thị câu trả lời giả.
**And** `data/sample/corpus.schema.json` + `corpus.json` mẫu tồn tại; backend đọc `corpus.json` lúc startup, thiếu file → fail fast với log rõ (AD-1, AD-2).
**And** key LLM đọc từ `.env` backend, không có key nào ở frontend (AD-8).

### Story 1.2: Kết nối pipeline với Repository (Epic 0)
As a hệ thống,
I want pipeline gọi interface `repository` của Epic 0 thay vì tự dựng KnowledgeBase in-memory,
So that logic dữ liệu (tìm kiếm, hiệu lực, quan hệ, xung đột) dùng một nguồn duy nhất là Postgres.

**Acceptance Criteria:**

**Given** `repository.py` của Epic 0 (hoặc stub tạm) sẵn có,
**When** backend khởi động,
**Then** tạo một handle repository dùng chung (connection pool), không mở kết nối tùy tiện mỗi request.
**And** pipeline **chỉ import `repository`**, không import psycopg/SQL trực tiếp (AD-7 layering).
**And** có **stub repository** (dữ liệu cứng đúng chữ ký hàm) để chạy khi Epic 0 chưa xong; thay bằng repository thật KHÔNG đổi chữ ký (hợp đồng `Clause` khóa ở Story 0.4).
**And** as-of/visibility là tham số truyền xuống `repository.search(...)`, không xử lý lại ở pipeline (tránh trùng logic với Epic 0).

### Story 1.3: Hybrid retrieve + expand dẫn chiếu
As a nhân viên,
I want hệ thống tìm điều khoản liên quan và tự kéo điều được dẫn chiếu,
So that câu trả lời không sót ngữ cảnh.

**Acceptance Criteria:**

**Given** một câu hỏi,
**When** chạy stage `retrieve` (Postgres full-text) rồi `expand`,
**Then** trả `List[Candidate]` với `score` chuẩn hóa `[0,1]` (AD-10), ranking chỉ ở `retrieve`.
**And** nếu một Candidate có cạnh `REFERENCES`, điều được dẫn chiếu được kéo vào kết quả (FR-5) — kiểm bằng `TT41/Điều 10` → kéo `TT41/Điều 6.3`.

### Story 1.4: Lọc as-of + thay thế một phần
As a cán bộ tuân thủ,
I want chỉ nhận điều khoản còn hiệu lực tại thời điểm hỏi,
So that không áp nhầm bản đã hết hiệu lực.

**Acceptance Criteria:**

**Given** kết quả sau retrieve/expand và `asOf` (mặc định hôm nay),
**When** chạy stage `temporal_filter`,
**Then** loại mọi Candidate có `is_active=false` (FR-8) — `TT41/Điều 6.3` (8%) bị loại, `TT22/Điều 1` (9%) giữ lại.
**And** với thay thế một phần, `TT41/Điều 8.2` bị loại còn `TT41/Điều 8.1` giữ lại (FR-9).
**And** đổi `asOf` về quá khứ (VD 2022-06-01) trả kết quả cũ tương ứng.

### Story 1.5: Tổng hợp câu trả lời + trích nguồn
As a nhân viên,
I want câu trả lời tiếng Việt kèm nguồn tới cấp Điều/Khoản,
So that tôi tin và trích được vào hồ sơ.

**Acceptance Criteria:**

**Given** tập điều khoản sạch sau temporal_filter,
**When** chạy stage `synthesize` (LLM),
**Then** trả `{answer}` tiếng Việt và `sources[]={clause_id, name, description}` (FR-4, FR-6).
**And** không có câu trả lời "thành công" nào thiếu `sources` (NFR-5).
**And** lời gọi LLM đi qua `providers/llm.py` (interface), có chế độ mock (AD-7, AD-9).

### Story 1.6: Giao diện chat + hiển thị nguồn + AsOfPicker + fallback
As a nhân viên,
I want khung chat hiển thị câu trả lời, nguồn bấm được, chọn mốc thời gian, và không trắng màn khi lỗi,
So that trải nghiệm tra cứu rõ ràng và đáng tin.

**Acceptance Criteria:**

**Given** giao diện Trợ lý (desktop-first 2 cột),
**When** người dùng gửi câu hỏi,
**Then** hiện ChatBubble + SourceCard (chip mono `clause_id`, StatusBadge trạng thái) theo token DESIGN.md (UX-DR1,2,3,4,5,15).
**And** có **AsOfPicker** đổi `asOf` và gửi lại truy vấn (UX-DR10).
**And** khi API lỗi/timeout 15s → chuyển fallback canned + báo "đang dùng bản đã lưu" (NFR-3, UX-DR12,14).
**And** trạng thái đã-thay-thế hiển thị gạch ngang + badge, không chỉ bằng màu (UX-DR13).

### Story 1.7: Chế độ khách hàng (công khai)
As a khách hàng,
I want tra cứu quy định công khai qua cùng giao diện,
So that tôi được trả lời mà không chạm dữ liệu nội bộ.

**Acceptance Criteria:**

**Given** **ModeToggle** đặt "Khách hàng",
**When** gửi câu hỏi,
**Then** `retrieve` lọc `visibility="public"` ngay từ đầu; `expand` không vượt sang clause `internal` (AD-11, FR-7).
**And** mọi `sources` trả về đều `public` — `QD-INT/Điều 2` không xuất hiện.
**And** thanh trên đổi nhãn "Chế độ công khai" (UX-DR10).

## Epic 2: Thấy quan hệ & lịch sử điều khoản

Mục tiêu: xem đồ thị quan hệ và dòng thời gian phiên bản; bấm nguồn highlight node.

### Story 2.1: Trực quan đồ thị tri thức
As a người dùng,
I want thấy văn bản và quan hệ dưới dạng đồ thị,
So that hiểu được cấu trúc sửa đổi/thay thế/dẫn chiếu.

**Acceptance Criteria:**

**Given** JSON `{nodes, edges}` từ KnowledgeBase,
**When** mở tab Đồ thị tri thức,
**Then** render react-force-graph-2d, node = văn bản/điều khoản, cạnh màu theo loại quan hệ (FR-12, UX-DR7).
**And** bấm node hiện chi tiết điều khoản + mở timeline của nó.
**And** có bảng danh sách quan hệ thay thế cho người không thao tác đồ hình (UX-DR13).

### Story 2.2: Dòng thời gian phiên bản điều khoản
As a cán bộ tuân thủ,
I want xem một điều khoản đã tiến hóa qua các bản nào,
So that hiểu vì sao bản hiện hành khác bản cũ.

**Acceptance Criteria:**

**Given** một `clause_id` có chuỗi `SUPERSEDED_BY`,
**When** mở tab Dòng thời gian,
**Then** hiện các phiên bản theo thời gian với ngày hiệu lực; bản hiện hành nổi bật, bản cũ mờ + gạch ngang (FR-10, UX-DR8).
**And** với `ty_le_an_toan_von`: hiện 8% (2016→2023) → 9% (2023→nay).

### Story 2.3: Bấm nguồn ↔ highlight node (hai chiều)
As a người dùng,
I want bấm SourceCard để nhảy tới node đồ thị và ngược lại,
So that liên kết câu trả lời với cấu trúc quan hệ.

**Acceptance Criteria:**

**Given** một câu trả lời có nguồn và đồ thị đang mở,
**When** bấm SourceCard,
**Then** node tương ứng được highlight/nhấp nháy; bấm node cũng highlight SourceCard (FR-13, UX-DR4).

## Epic 3: Cảnh báo xung đột

Mục tiêu: cảnh báo khi hai quy định cùng hiệu lực mâu thuẫn số liệu.

### Story 3.1: Rule phát hiện xung đột
As a hệ thống,
I want quét dữ liệu để phát hiện điều khoản cùng chủ đề, cùng hiệu lực nhưng khác giá trị số,
So that cảnh báo được mâu thuẫn thật.

**Acceptance Criteria:**

**Given** tập điều khoản còn hiệu lực,
**When** chạy stage `conflict_check` (sau `temporal_filter`),
**Then** với các clause cùng `topic` và cùng active, so sánh `metric.value`; khác nhau → gắn cờ xung đột (FR-11, AD-3).
**And** phát hiện `TT22/Điều 1` (9%) vs `QD-INT/Điều 2` (8%) — rule **quét thật**, không hardcode (NFR-7).
**And** chịu được ≥1 ca dựng thêm không xem trước; ca "bản cũ vs bản mới" KHÔNG bị coi là xung đột (đã do temporal xử).

### Story 3.2: Hiển thị banner cảnh báo xung đột
As a nhân viên,
I want thấy cảnh báo rõ khi có xung đột,
So that tôi thận trọng trước khi áp dụng.

**Acceptance Criteria:**

**Given** `conflictWarning` khác null,
**When** hiển thị câu trả lời,
**Then** hiện ConflictBanner (amber, icon ⚠) liệt kê 2 nguồn mâu thuẫn (FR-13, UX-DR6).
**And** banner không chiếm toàn màn, có nút "xem chi tiết".

## Epic 4: Chứng minh hơn RAG thường (Benchmark)

Mục tiêu: đặt cạnh RAG baseline để lộ khác biệt, đa bằng chứng.

### Story 4.1: Chế độ baseline (tắt expand + temporal)
As a người trình bày,
I want chạy cùng pipeline với `mode=baseline` (tắt expand + temporal),
So that có đối chứng RAG thường trung thực.

**Acceptance Criteria:**

**Given** một câu hỏi và `mode=baseline`,
**When** gọi `/api/chat`,
**Then** pipeline bỏ qua `expand` và `temporal_filter`, giữ nguyên retrieve+synthesize (FR-14, AD-3).
**And** cùng câu bẫy: baseline trả 8% (bản cũ), `mode=system` trả 9% + cảnh báo (NFR-6: baseline không bị làm yếu giả tạo).

### Story 4.2: Màn benchmark 2 cột + đa bằng chứng
As a ban giám khảo,
I want thấy hai kết quả cạnh nhau cho cùng câu hỏi,
So that thấy ngay khác biệt.

**Acceptance Criteria:**

**Given** màn Benchmark,
**When** nhập câu hỏi,
**Then** hiện 2 cột đồng bộ (RAG thường / Copilot), tô chỗ khác biệt (FR-14, UX-DR9).
**And** có sẵn ≥1 bằng chứng KHÔNG cần delta số: B (thay thế một phần) và/hoặc C (dẫn chiếu) (FR-15).

## Epic 5: Quản trị nội dung (Admin/Ingest)

Mục tiêu: nạp văn bản mới qua UI, cập nhật đồ thị an toàn.

### Story 5.1: Nạp văn bản qua Admin (Streamlit) + atomic swap
As a admin nội dung,
I want nạp/cập nhật văn bản qua giao diện,
So that đưa quy định mới vào hệ thống không cần chạm code.

**Acceptance Criteria:**

**Given** màn Admin (Streamlit),
**When** nạp một văn bản/JSON mới,
**Then** dựng KnowledgeBase mới rồi **atomic swap** `current_kb`; request đang chạy không bị ảnh hưởng (FR-3, AD-2, UX-DR11).
**And** hiện thông báo "đã nạp, đồ thị cập nhật" + có nút "Chạy Radar".

## Epic 6 (STRETCH): Radar Tác động

Mục tiêu: báo cáo tác động khi nạp văn bản mới. Chỉ làm sau Epic 1–5.

### Story 6.1: Báo cáo tác động lan tỏa
As a admin,
I want thấy văn bản mới ảnh hưởng tới điều khoản/văn bản nào,
So that biết cần cập nhật gì mà không dò tay.

**Acceptance Criteria:**

**Given** một văn bản sửa đổi vừa nạp,
**When** bấm "Chạy Radar",
**Then** duyệt đồ thị và liệt kê đúng điều khoản/văn bản bị ảnh hưởng theo cạnh quan hệ (FR-16).
**And** kịch bản deterministic (input chuẩn bị chắc kích hoạt), tính từ đồ thị runtime, không hardcode output (AD-9, NFR-7).

## UX-DR Coverage
- UX-DR1,2,3,4,5,15 → Story 1.6 · UX-DR7 → 2.1 · UX-DR8 → 2.2 · UX-DR4 → 2.3 · UX-DR6 → 3.2 · UX-DR9 → 4.2 · UX-DR10 → 1.6/1.7 · UX-DR11 → 5.1/6.1 · UX-DR12,14 → 1.6 · UX-DR13 → 1.6/2.1 (AC a11y) · UX-DR16 (mock) → tham chiếu Story 1.6.
