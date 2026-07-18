---
title: "PRD: Trợ lý tra cứu văn bản ngân hàng thông minh (IBIB - VIC 2026)"
status: final
created: 2026-07-17
updated: 2026-07-17
---

# PRD: Trợ lý tra cứu văn bản ngân hàng thông minh
*Working title — xác nhận.*

## 0. Document Purpose

PRD này dành cho nhóm IBIB (6 người) và các bước downstream (architecture, epics/stories, sprint planning) trong khuôn khổ hackathon **Vietnam AI Innovation Challenge 2026 — 48 giờ**, đề bài SHB *Advanced RAG Knowledge Base*. Tài liệu tổ chức theo: Glossary neo thuật ngữ → Features gom theo **7 epic tầng build**, FR đánh số toàn cục (FR-N) → NFR cross-cutting → Metrics theo tiêu chí thi. PRD này **xây trên** `brief.md` và `addendum.md` tại `_bmad-output/planning-artifacts/briefs/brief-ibib-vic-2026-2026-07-17/`; chi tiết *cách xây* (tech stack, schema đồ thị, bảng mức-co-tối-thiểu, rủi ro H0) nằm ở addendum của brief và không lặp lại ở đây. PRD chỉ nói *năng lực*, không nói *triển khai*.

## 1. Vision

Nhân viên ngân hàng SHB phải tra cứu hàng nghìn văn bản pháp lý luôn biến động — sửa đổi, thay thế một phần, dẫn chiếu, mâu thuẫn lẫn nhau. RAG thường chỉ tìm đoạn "giống câu hỏi nhất" nên dễ trả về điều khoản đã hết hiệu lực, gây rủi ro tuân thủ. Sản phẩm là một **trợ lý pháp lý** cho phép hỏi bằng tiếng Việt tự nhiên và nhận câu trả lời **đúng quy định đang có hiệu lực, kèm trích dẫn nguồn tới cấp Điều/Khoản**.

Cốt lõi khác biệt không phải "một LLM mới", mà là một **đồ thị tri thức có chiều thời gian**: mỗi điều khoản mang khoảng hiệu lực và các quan hệ sửa đổi/thay thế/dẫn chiếu ở cấp khoản. Nhờ lớp này, hệ thống dựng lại được trạng thái luật tại bất kỳ thời điểm nào, loại đúng điều khoản đã bị thay thế một phần, tự nối điều được dẫn chiếu, và cảnh báo xung đột — những việc RAG ngữ nghĩa thuần không làm được.

Trong phạm vi 48h, sản phẩm phải chứng minh giá trị bằng **demo chạy thật**: sáu deliverable đề yêu cầu đều hoạt động và bấm được, kèm màn benchmark đặt cạnh RAG thường để cho thấy khác biệt. Lớp sáng tạo mở rộng (Radar Tác động — chủ động cảnh báo khi luật đổi) là điểm cộng, làm sau khi phần bắt buộc chạy.

## 2. Target User

### 2.1 Jobs To Be Done
- **Cán bộ tuân thủ / pháp chế:** biết chắc quy định nào đang có hiệu lực *ngay lúc này*, có nguồn để trích, không áp nhầm bản cũ → tránh rủi ro phạt.
- **Cán bộ tín dụng / nghiệp vụ:** tra cứu nhanh quy định để xử lý hồ sơ hằng ngày, tin được câu trả lời vì có dẫn nguồn.
- **Admin nội dung:** đưa văn bản mới/sửa đổi vào hệ thống mà không cần chạm code.
- **Khách hàng (thứ cấp):** tra cứu quy định/chính sách công khai liên quan đến sản phẩm, giới hạn ở dữ liệu công khai.

### 2.2 Non-Users (v1)
- Không phục vụ soạn thảo/ban hành văn bản pháp luật.
- Không phải công cụ tư vấn pháp lý thay luật sư; chỉ tra cứu + trích nguồn để người dùng tự quyết.

### 2.3 Key User Journeys

- **UJ-1. Hà (cán bộ tuân thủ) kiểm tra một ngưỡng đang hiệu lực.**
  - **Persona + context:** Hà rà soát hồ sơ, cần con số quy định *hiện hành*, sợ nhất là dùng nhầm bản đã bị sửa.
  - **Path:** mở giao diện chat → hỏi "Tỷ lệ an toàn vốn tối thiểu hiện nay là bao nhiêu?" → hệ thống tìm, lọc theo hiệu lực hôm nay, tổng hợp.
  - **Climax:** nhận câu trả lời theo **bản sửa đổi mới nhất**, kèm trích dẫn Điều/Khoản/văn bản và cảnh báo "điều khoản cũ đã bị thay thế".
  - **Resolution:** Hà tin và trích thẳng nguồn vào hồ sơ.

- **UJ-2. Nam (cán bộ tín dụng) chạm điều khoản bị thay thế một phần.**
  - **Path:** hỏi về một quy trình mà một khoản của nó đã bị bãi bỏ → hệ thống trả lời chỉ dùng phần còn hiệu lực, **không đưa khoản đã bị bãi bỏ**, và ghi rõ khoản nào đã hết hiệu lực.
  - **Climax:** Nam thấy hệ thống loại đúng khoản chết mà RAG thường vẫn trả.

- **UJ-3. Linh (khách hàng) hỏi một chính sách công khai.**
  - **Path:** dùng cùng giao diện ở **chế độ chỉ-dữ-liệu-công-khai** → hỏi một quy định đã công bố → nhận trả lời có nguồn, không chạm dữ liệu nội bộ.

- **UJ-4. Tú (admin) nạp một văn bản sửa đổi mới.** *(kích hoạt Radar — Epic 7 stretch)*
  - **Path:** tải văn bản mới qua màn admin → hệ thống cập nhật đồ thị → **Radar** bắn báo cáo: điều khoản/văn bản nào bị ảnh hưởng.
  - **Climax:** Tú thấy tác động lan tỏa mà không phải tự dò thủ công.

## 3. Glossary

- **Văn bản (Document)** — một văn bản pháp lý (Luật/Nghị định/Thông tư/Basel...), có ngày ban hành và ngày hiệu lực.
- **Điều khoản (Clause)** — đơn vị nội dung cấp Điều/Khoản/Điểm thuộc một Văn bản; mang khoảng hiệu lực và trạng thái.
- **Khoảng hiệu lực** — cặp [ngày bắt đầu hiệu lực, ngày hết hiệu lực) gắn cho mỗi Điều khoản.
- **As-of date** — mốc thời gian dùng để lọc; mặc định là hôm nay. Truy vấn chỉ giữ Điều khoản còn hiệu lực tại as-of.
- **Sửa đổi (Amendment)** — quan hệ khi một Văn bản thay đổi nội dung một Điều khoản của Văn bản khác.
- **Thay thế / Thay thế một phần (Supersession / Partial supersession)** — một Điều khoản (hoặc một phần) bị bãi bỏ/thay, phần còn lại vẫn hiệu lực. *Cạnh đồ thị:* `SUPERSEDES`; *quan hệ phiên bản:* `SUPERSEDED_BY` (bản cũ → bản mới). Toàn PRD dùng đúng các định danh này, không dùng từ đồng nghĩa khác.
- **Dẫn chiếu (Reference)** — quan hệ khi một Điều khoản trỏ tới Điều khoản/Văn bản khác.
- **Xung đột (Conflict)** — hai Điều khoản cùng hiệu lực quy định giá trị mâu thuẫn về cùng một chủ đề.
- **Đồ thị tri thức** — tập Văn bản + Điều khoản (nodes) và các quan hệ Sửa đổi/Thay thế/Dẫn chiếu/Xung đột (edges), có gắn chiều thời gian.
- **Hybrid search** — tìm kiếm kết hợp từ khóa + ngữ nghĩa + duyệt đồ thị.
- **RAG baseline** — cấu hình đối chứng chạy trên cùng dữ liệu, cùng pipeline, **tắt** bước lọc hiệu lực và duyệt dẫn chiếu.
- **Trích nguồn (Citation)** — dẫn chiếu câu trả lời về đúng Điều/Khoản/Văn bản gốc.
- **Radar Tác động** — tính năng chủ động: khi nạp Văn bản mới, liệt kê Điều khoản/Văn bản bị ảnh hưởng.

## 4. Features

*FR đánh số toàn cục. Mỗi Consequence là điều kiện kiểm thử được. Nhiều FR nêu hai mức: **[Mức co]** (nếu cháy giờ) và **[Đầy đủ]**, khớp bảng mức-co-tối-thiểu ở brief addendum.*

### 4.1 Epic 1 — Nền dữ liệu, Ingestion & Đồ thị tri thức
**Description:** Nạp bộ văn bản mẫu, cắt theo cấu trúc pháp lý, gắn quan hệ + khoảng hiệu lực (hand-annotate cho 48h), và dựng đồ thị tri thức phục vụ mọi tính năng phía sau. Bao gồm màn admin/ingest (deliverable "Admin dashboard"). Hiện thực hóa UJ-4.

#### FR-1: Cắt văn bản theo cấu trúc Điều/Khoản/Điểm
Hệ thống cắt mỗi Văn bản thành các Điều khoản theo cấu trúc pháp lý, không theo token cố định.
**Consequences (testable):**
- Mỗi chunk gắn được `path` dạng "Điều 5.3" và `doc_id`.
- Không có chunk nào cắt ngang giữa một Khoản.

#### FR-2: Gắn quan hệ & khoảng hiệu lực cho Điều khoản
Admin/hệ thống gán các cạnh Sửa đổi/Thay thế/Dẫn chiếu và cặp [effective_date, expiry_date) cho từng Điều khoản.
**Consequences:**
- Khi một Văn bản sửa đổi được nạp, Điều khoản bị thay được set `expiry_date = effective_date` của bản mới, và tạo cạnh SUPERSEDED_BY old→new.
- Đồ thị serialize được ra JSON `{nodes, edges}` dùng chung cho backend và frontend.

#### FR-3: Nạp văn bản mới qua màn admin *(deliverable: Admin dashboard)*
Admin có thể đưa một Văn bản mới vào hệ thống qua giao diện, không cần chạm code.
**Consequences:**
- **[Đầy đủ]** UI ingest (upload/nhập) cập nhật đồ thị và kho tìm kiếm.
- **[Mức co]** Nạp từ file JSON đã chuẩn bị sẵn, hệ thống đọc lúc khởi động.
**Out of Scope:** trích quan hệ tự động từ PDF thô (xem Non-Goals).

### 4.2 Epic 2 — Retrieval & Chatbot Hỏi–đáp có trích nguồn
**Description:** Bề mặt chính người dùng: hỏi tự nhiên, hệ thống hybrid search + duyệt dẫn chiếu, LLM tổng hợp, trả lời kèm trích nguồn qua `POST /api/chat`. Hiện thực hóa UJ-1, UJ-3.

#### FR-4: Hỏi–đáp bằng tiếng Việt tự nhiên qua API
Người dùng gửi câu hỏi, nhận câu trả lời tổng hợp bằng tiếng Việt.
**Consequences:**
- Endpoint `POST /api/chat` nhận `{question}` và trả `{answer, sources[...]}` đúng `API_CONTRACT.md`.
- Câu trả lời là chuỗi khi thành công (HTTP 200). Lỗi trả đúng mã theo `API_CONTRACT.md`: 400 (request sai), 422 (đầu vào không hợp lệ), 500 (xử lý thất bại), 503 (tạm không khả dụng), kèm trường `detail`.
- Backend đặt header CORS cho phép địa chỉ frontend (mặc định `http://localhost:5173`).

#### FR-5: Hybrid search + duyệt dẫn chiếu
Hệ thống tìm kiếm kết hợp từ khóa + ngữ nghĩa và mở rộng theo cạnh Dẫn chiếu 1–2 hop.
**Consequences:**
- Với câu hỏi trỏ tới một Điều có Dẫn chiếu, kết quả chứa cả Điều được dẫn chiếu.
- **[Mức co]** Postgres full-text (`ts_rank`) + LLM; **[Đầy đủ]** thêm dense vector + RRF.

#### FR-6: Trích nguồn tới cấp Điều/Khoản *(deliverable: chatbot có trích nguồn)*
Mọi câu trả lời dẫn được về đúng Điều/Khoản/Văn bản nguồn.
**Consequences:**
- Mỗi phần tử `sources` có tên nguồn + định danh Điều/Khoản.
- Không có câu trả lời "thành công" nào thiếu nguồn.

#### FR-7: Chế độ chỉ-dữ-liệu-công-khai cho khách hàng
Ở chế độ khách hàng, hệ thống chỉ truy vấn Văn bản gắn nhãn công khai.
**Consequences:**
- Một câu hỏi khách hàng demo trả lời chỉ từ dữ liệu công khai, không lộ Văn bản nội bộ. Hiện thực hóa UJ-3.
- Kiểm được: ở chế độ khách hàng, mọi phần tử `sources` đều mang nhãn `public`; không nguồn nào gắn nhãn nội bộ.

### 4.3 Epic 3 — Thời gian & Phiên bản điều khoản
**Description:** Lõi khác biệt: lọc theo as-of, xử lý thay thế một phần, và dựng dòng thời gian phiên bản. Hiện thực hóa UJ-1, UJ-2.

#### FR-8: Lọc theo hiệu lực (as-of date)
Truy vấn chỉ trả về Điều khoản còn hiệu lực tại as-of (mặc định hôm nay).
**Consequences:**
- Điều khoản có `expiry_date <= asOf` không xuất hiện trong câu trả lời.
- **[Đầy đủ]** người dùng chọn được as-of trong quá khứ và kết quả đổi tương ứng.

#### FR-9: Loại đúng điều khoản bị thay thế một phần
Khi một Khoản bị bãi bỏ, hệ thống loại đúng Khoản đó và giữ phần còn hiệu lực.
**Consequences:**
- Câu trả lời cho UJ-2 không chứa Khoản đã bị bãi bỏ, và nêu rõ Khoản nào đã hết hiệu lực.

#### FR-10: Dòng thời gian phiên bản điều khoản *(deliverable: clause version timeline)*
Hệ thống cho xem một Điều khoản đã tiến hóa qua các bản nào (duyệt chuỗi SUPERSEDED_BY).
**Consequences:**
- **[Đầy đủ]** timeline đồ họa; **[Mức co]** danh sách các phiên bản theo thứ tự thời gian, có ngày hiệu lực.

### 4.4 Epic 4 — Phát hiện xung đột
**Description:** Rule quét thật trên dữ liệu để cảnh báo hai Điều khoản cùng hiệu lực mâu thuẫn số liệu; tùy chọn LLM judge giảm false positive. *(deliverable: Conflict detector)*

#### FR-11: Quét & cảnh báo xung đột
Hệ thống đối chiếu các Điều khoản cùng chủ đề & cùng hiệu lực, cảnh báo khi giá trị số mâu thuẫn.
**Consequences:**
- Mỗi Điều khoản mang một nhãn `topic` trong dữ liệu; "cùng chủ đề" = trùng nhãn `topic` (kiểm được), rule chỉ so sánh giá trị số giữa các Điều khoản cùng `topic` và cùng hiệu lực.
- Rule **duyệt dữ liệu thật** (không nhét cứng kết quả), phát hiện được cả một ca dựng thêm không xem trước.
- Chuẩn bị **≥2 ca xung đột** chạy thật; UI hiển thị banner cảnh báo kèm 2 nguồn.
- **[Đầy đủ]** thêm LLM judge để giảm báo nhầm.
**Out of Scope:** engine phát hiện mọi loại mâu thuẫn ngữ nghĩa (chỉ tập trung mâu thuẫn giá trị số).

### 4.5 Epic 5 — Trực quan hóa
**Description:** Các bề mặt hiển thị: đồ thị tri thức tương tác, timeline, banner xung đột, khối trích nguồn. *(deliverable: Knowledge graph visualization)*

#### FR-12: Trực quan đồ thị tri thức
Hiển thị Văn bản và quan hệ (sửa đổi/thay thế/dẫn chiếu) dưới dạng đồ thị.
**Consequences:**
- **[Đầy đủ]** đồ thị tương tác (bấm node xem chi tiết) từ JSON; **[Mức co]** đồ thị tĩnh.

#### FR-13: Hiển thị trích nguồn & cảnh báo trong giao diện
Giao diện chat hiển thị danh sách nguồn cho mỗi câu trả lời và banner khi có xung đột/điều khoản đã thay thế.
**Consequences:**
- Người dùng bấm được vào nguồn để xem Điều/Khoản gốc.

### 4.6 Epic 6 — Benchmark vs RAG thường
**Description:** Đặt hệ thống cạnh RAG baseline trên cùng dữ liệu để chứng minh khác biệt, **đa bằng chứng** (không phụ thuộc riêng cái bẫy số). *(deliverable: Benchmark comparison)*

#### FR-14: Chạy đối chứng cạnh nhau
Cùng một câu hỏi chạy qua hệ thống và qua RAG baseline, hiển thị hai kết quả side-by-side.
**Consequences:**
- RAG baseline = cùng data, cùng pipeline, **tắt** lọc hiệu lực + duyệt dẫn chiếu (không làm yếu giả tạo).
- **[Mức co]** 1 cặp câu; **[Đầy đủ]** bộ ~20–30 câu "bẫy thời gian".

#### FR-15: Đa bằng chứng khác biệt
Bộ demo có ít nhất một bằng chứng KHÔNG cần giá trị số đổi.
**Consequences:**
- Bằng chứng B (thay thế một phần): hệ thống loại đúng Khoản chết, baseline vẫn trả.
- Bằng chứng C (dẫn chiếu): hệ thống tự kéo Điều được dẫn chiếu, baseline bỏ sót.
- Bằng chứng A (bẫy số) chỉ dùng nếu giá trị số thật sự đổi; nếu là amendment dựng thì **trình bày trung thực**.

### 4.7 Epic 7 (STRETCH) — Radar Tác động
**Description:** Lớp sáng tạo, **chỉ làm sau khi Epic 1–6 chạy ổn**. Khi admin nạp Văn bản sửa đổi, hệ thống lan tỏa trên đồ thị và báo cáo tác động. Hiện thực hóa UJ-4. Ngoài 6 deliverable đề yêu cầu.

#### FR-16: Báo cáo tác động khi nạp văn bản mới
Nạp một Văn bản sửa đổi → liệt kê Điều khoản/Văn bản bị ảnh hưởng.
**Consequences:**
- Kịch bản deterministic (chuẩn bị sẵn, **không hardcode output**): với văn bản demo, báo cáo liệt kê đúng tập bị ảnh hưởng theo cạnh đồ thị.
- **[NON-GOAL for MVP]** đối chiếu quy định nội bộ vs luật ngoài (Máy Dò Lệch Chuẩn) và Văn bản Hợp nhất Sống — chỉ nếu còn thời gian.

## 5. Non-Goals (Explicit)
- **Không huấn luyện/tự chế LLM** — dùng LLM qua API.
- **Không trích quan hệ pháp lý tự động từ PDF thô** trong 48h — quan hệ được hand-annotate; parser chỉ là stretch.
- **Không tích hợp toàn bộ kho văn bản thật của SHB** — chỉ dùng bộ mẫu 5–10 văn bản.
- **Không làm phân quyền/bảo mật cấp doanh nghiệp** — chỉ nêu nguyên tắc (API key ở backend).
- **Không trở thành công cụ tư vấn pháp lý** — chỉ tra cứu + trích nguồn.
- **Không dựng graph DB (Neo4j) hay vector DB server (Qdrant)** — dùng **PostgreSQL** làm lớp dữ liệu (quan hệ + full-text + thời gian); truy cập qua tầng repository (xem Architecture Spine AD-2/AD-7/AD-12). *(Cập nhật: đổi từ in-memory sang PostgreSQL.)*

## 6. MVP Scope

### 6.1 In Scope
- Bộ 5–10 văn bản mẫu có tình huống *sửa đổi*, *thay thế một phần*, *dẫn chiếu*, và ≥1 ca *xung đột*.
- Epic 1–6 (sáu deliverable đề yêu cầu) ở mức "hoạt động và bấm được", mỗi mục có mức co tối thiểu.
- Chatbot nối frontend qua `POST /api/chat`, gồm một câu hỏi khách hàng ở chế độ công khai.
- Màn benchmark đa bằng chứng.
- Phương án dự phòng demo (mock mode + câu trả lời canned cho câu demo chính).
- **[NOTE FOR PM]** Khối trực quan FE (đồ thị, timeline, banner, màn benchmark, admin) dựng gần như từ đầu trên khung chat sẵn có — là phần nặng và ảnh hưởng trực tiếp SM-1; khởi động **song song ngay H0** với data + backend, không dồn về cuối. Benchmark (FR-14/15) nằm cuối chuỗi phụ thuộc nên dựng harness 2 cột bằng data giả sớm.

### 6.2 Out of Scope for MVP
- Radar Tác động (Epic 7) — **[NOTE FOR PM]** chỉ làm sau khi Epic 1–6 chạy; là điểm cộng sáng tạo, đừng đánh đổi phần bắt buộc.
- Máy Dò Lệch Chuẩn, Văn bản Hợp nhất Sống — hướng mở rộng v2.
- Citation parser tự động, LLM judge xung đột — nâng cấp nếu dư giờ.
- Tích hợp toàn bộ kho văn bản thật, phân quyền doanh nghiệp.

## 7. Success Metrics

*Đo bằng tiêu chí demo/thi (đề chưa công bố khung chấm chính thức); giá trị kinh doanh để định tính.*

**Primary**
- **SM-1: Độ phủ deliverable** — cả 6 deliverable (Epic 1–6) hiện diện và bấm được trong demo. Validates FR-3, FR-6, FR-10, FR-11, FR-12, FR-14.
- **SM-2: Khác biệt chứng minh được** — ≥2 loại bằng chứng benchmark chạy thật, trong đó ≥1 loại không cần giá trị số đổi. Validates FR-14, FR-15, FR-8, FR-9.
- **SM-3: Đúng hiệu lực + có nguồn** — trên bộ câu hỏi demo, câu trả lời dùng đúng bản còn hiệu lực và mọi câu đều có trích nguồn đúng Điều/Khoản. Validates FR-6, FR-8, FR-9.

**Secondary**
- **SM-4: Thời gian phản hồi** — P95 < 15 giây/câu ở chế độ demo. Validates FR-4.
- **SM-5: Xung đột chịu ca lạ** — bộ phát hiện xung đột xử đúng ≥1 ca giám khảo nêu tại chỗ (không xem trước). Validates FR-11.

**Counter-metrics (không tối ưu)**
- **SM-C1: Đừng đánh bóng Radar khi deliverable còn thiếu** — số giờ đổ vào Epic 7 không được vượt phần Epic 1–6 chưa xong. Cân bằng SM-1.
- **SM-C2: Đừng làm baseline yếu giả tạo** — RAG baseline phải cùng data/pipeline; không "dàn trận" để mình thắng. Cân bằng SM-2.
- **SM-C3: Đừng phồng phạm vi** — thêm tính năng ngoài 6 deliverable trước khi chúng chạy là phản chỉ định. Cân bằng SM-1.

## 8. Open Questions
1. **Bộ văn bản demo & bẫy số (rủi ro H0).** Chưa có file. Có tồn tại một giá trị số thật đổi giữa hai bản (ví dụ CAR giữa TT41 và bản sửa đổi) để làm bằng chứng A? Nếu không, dựng amendment tổng hợp và trình bày trung thực. (Đã có lưới an toàn B/C.)
2. **Khung chấm điểm chính thức** của ban tổ chức — cập nhật khi có, để tinh chỉnh trọng số.
3. **Sáu deliverable có vừa 48h/6 người không** — phụ thuộc phân công; bảng mức-co-tối-thiểu là van an toàn.
4. **Danh sách văn bản gắn nhãn "công khai"** cho chế độ khách hàng (FR-7) — cần chọn ít nhất một.

## 9. Assumptions Index
- **[GIẢ ĐỊNH] §1/§7:** ưu tiên chấm điểm là *khả thi + demo thật* và *độ mới* (nhóm tự đặt, chưa có khung chính thức).
- **[GIẢ ĐỊNH] §6.1:** bộ mẫu 5–10 văn bản là đủ để phủ cả 4 tình huống khác biệt.
- **[GIẢ ĐỊNH] §4.2 FR-4:** giữ đúng contract `POST /api/chat` hiện có; nếu đổi schema phải thống nhất lại FE.
- **[GIẢ ĐỊNH] §4.7:** Radar chỉ cần một kịch bản deterministic là đủ ăn điểm "độ mới".
- **[GIẢ ĐỊNH] §2.1:** khách hàng là người dùng thứ cấp, chỉ một khoảnh khắc demo công khai.
- **[GIẢ ĐỊNH] §4.6/§8.1:** nếu dữ liệu thật thiếu delta số, dùng amendment tổng hợp (gắn nhãn rõ là kịch bản dựng) cho bằng chứng A; bằng chứng B/C không phụ thuộc giả định này.

---

## 10. Cross-Cutting NFRs
- **Hiệu năng:** P95 < 15 giây/câu ở demo; ingest chạy offline, không tính vào thời gian phản hồi.
- **Bảo mật:** API key LLM chỉ ở backend, không lộ ra frontend; backend cho phép CORS tới địa chỉ FE; luôn trả JSON.
- **Độ tin cậy demo:** có mock mode + bộ câu trả lời canned cho các câu demo chính, để chịu được LLM API chậm/lỗi giữa pitch.
- **Ngôn ngữ:** nội dung và câu trả lời bằng tiếng Việt.
- **Provenance:** mọi câu trả lời truy vết được về nguồn (đồng nhất với FR-6) — thuộc tính lõi của sản phẩm tuân thủ.

## 11. Constraints & Guardrails
- **Trung thực dữ liệu:** nếu dùng amendment tổng hợp để tạo bẫy benchmark, phải gắn nhãn rõ là kịch bản dựng, và giá trị số phải nhất quán trong toàn bộ mẫu.
- **Không nhét cứng:** các màn "chạy thật" (xung đột, Radar) phải để logic quét/duyệt dữ liệu thật, không hardcode output. *"Deterministic" (FR-11, FR-16) nghĩa là kịch bản demo được chuẩn bị để CHẮC CHẮN kích hoạt logic — KHÔNG phải cài sẵn câu trả lời.*
- **Chi phí:** dùng LLM API theo lượt; giữ số lần gọi ở demo hợp lý (cân nhắc cache).
