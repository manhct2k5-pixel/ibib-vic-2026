---
title: "Review khả thi 48h — PRD IBIB VIC 2026"
status: draft
created: 2026-07-17
reviewer: feasibility (48h / 6 người)
scope: "Chỉ soi thực thi — làm kịp & demo thật. KHÔNG soi chất lượng văn bản."
---

# Review khả thi thực thi — PRD IBIB (VIC 2026, hackathon 48h, đội 6)

## Verdict tổng

**KỊP CÓ ĐIỀU KIỆN (rủi ro trung bình, kiểm soát được).**

PRD được thiết kế đúng tư duy hackathon: bảng "mức co tối thiểu" là van an toàn thật sự, đã cắt đúng hai điểm tích hợp dễ vỡ nhất (bỏ Neo4j + Qdrant), và hand-annotate dữ liệu thay vì auto-extract. Nếu team **kỷ luật tuân thủ thứ tự build + hạ về mức co ngay khi cháy giờ**, 6 deliverable ở mức "bấm được" là khả thi trong 48h/6 người.

Rủi ro không nằm ở PRD sai, mà ở **3 chỗ dễ trượt khi thực thi**:
1. Dữ liệu chưa tồn tại (critical path — cả nửa số FR treo vào nó).
2. Frontend hiện là **starter trần** — mọi màn trực quan (đồ thị, timeline, benchmark side-by-side, banner, admin) đều phải dựng từ 0 + thêm thư viện; đây là khối FE bị PRD ngầm đánh giá thấp.
3. Cám dỗ đánh bóng phần "wow" (hybrid RRF, đồ thị tương tác, Radar) trước khi mức co của 6 deliverable chạy hết.

Nếu buông kỷ luật mức co → tụt xuống "khó kịp".

---

## Bối cảnh repo (đã kiểm chứng tại H0)

- `backend/` — **trống** (chỉ `.gitkeep`). Toàn bộ FastAPI + pipeline chưa có dòng nào.
- `data/sample/` — **trống** (chỉ `.gitkeep`). Không có văn bản mẫu, không có JSON đồ thị.
- `tests/evaluation/` — **trống**. Bộ câu hỏi benchmark chưa có.
- `frontend/` — React 19 + Vite starter. Chỉ có `App.tsx`, `services/chatApi.ts` (đã có switch mock/real). **CHƯA có** thư viện đồ thị (`react-force-graph`/`vis-network`), **chưa có** component timeline / benchmark / banner / admin. `package.json` chỉ có react + react-dom.
- `API_CONTRACT.md` — contract `POST /api/chat` `{question}` → `{answer, sources[], requestId, latencyMs}` đã rõ, FE mock đã bám theo. Đây là tài sản chắc chắn nhất.

Kết luận bối cảnh: điểm khởi đầu thực tế là **~0% backend, ~10% frontend** (chỉ khung chat + lớp gọi API). Ước lượng công của PRD nên đọc dưới lăng kính này.

---

## Danh sách rủi ro (xếp theo severity)

### CRITICAL

#### R1 — Bộ dữ liệu văn bản chưa tồn tại; là critical path chặn ~1/2 số FR
- **Liên quan:** Open Q1, §6.1, FR-1, FR-2, FR-5, FR-8, FR-9, FR-10, FR-11, FR-14, FR-15, FR-16.
- **Mô tả:** `data/sample/` trống. Không có JSON `{nodes, edges}` + khoảng hiệu lực → không FR nào của Epic 3 (as-of, thay thế một phần, timeline), Epic 4 (xung đột), Epic 6 (benchmark) demo được. Đồ thị (FR-12) và Radar (FR-16) cũng đọc từ chính JSON này. Dữ liệu vừa là input vừa là **kịch bản demo** (bằng chứng A/B/C, ≥2 ca xung đột, tập bị ảnh hưởng của Radar) — nghĩa là sai/thiếu dữ liệu không chỉ chặn build mà còn phá kịch bản pitch.
- **Mức đe dọa demo:** cao nhất. Đây là "single point of failure" của cả sản phẩm.
- **Giảm thiểu:**
  - Giao cho **người giỏi nhất về nghiệp vụ**, khởi động **ngay H0**, KHÔNG đợi backend.
  - Chốt ngay **schema JSON đóng băng** (nodes/edges/effective_date/expiry_date/path) để backend + FE code song song trên contract dữ liệu, không chờ dữ liệu thật hoàn thiện.
  - Curate **có mục tiêu**: mỗi văn bản/quan hệ phải phục vụ ít nhất 1 bằng chứng benchmark hoặc 1 ca xung đột. Không curate lan man.
  - Ưu tiên lưới an toàn: **1 khoản bị bãi bỏ một phần (B) + 1 quan hệ dẫn chiếu (C)** hand-annotate được ngay, không phụ thuộc luật thật. Đây là phần hạ R1 từ "sụp benchmark" xuống "mất 1/3 bằng chứng".
  - Bằng chứng A (delta số thật, ví dụ CAR TT41): nếu không tìm được số thật đổi trong 1–2 giờ, **dựng amendment tổng hợp gắn nhãn trung thực** ngay, đừng dừng chờ.

#### R2 — Frontend visualization bị đánh giá thấp: 4+ màn dựng từ 0 trên starter trần
- **Liên quan:** FR-10 (timeline), FR-12 (đồ thị), FR-13 (nguồn + banner), FR-14 (benchmark side-by-side), + màn admin (Epic 1 / Streamlit).
- **Mô tả:** PRD/addendum mô tả các màn này như "hiển thị từ JSON", ngầm giả định FE dễ. Thực tế repo chỉ có khung chat. Cần: thêm & học `react-force-graph`/`vis-network`, dựng component timeline, layout benchmark 2 cột, banner cảnh báo, khối citation bấm được, và admin (addendum chọn Streamlit → **tách stack Python riêng**, không dùng lại FE React). Đây là khối giờ FE lớn nhất và **dễ vỡ layout/tích hợp** hơn backend logic (vốn chỉ là filter + traverse trên tiny data).
- **Mức đe dọa demo:** cao — SM-1 (độ phủ 6 deliverable bấm được) phụ thuộc trực tiếp vào các màn này.
- **Giảm thiểu:**
  - Áp mức co **triệt để** ngay từ kế hoạch, không coi là phương án dự phòng: timeline = **danh sách** trước; đồ thị = **ảnh tĩnh/SVG** trước; benchmark = **1 cặp câu** trước; admin = **đọc JSON lúc startup** (bỏ Streamlit UI ingest nếu cần) — chỉ nâng cấp khi mọi mức co đã xanh.
  - Phân **≥2 người FE** chạy song song (một người graph+timeline, một người benchmark+banner+citation).
  - Chốt hình dạng JSON đồ thị **khớp thẳng props của react-force-graph** để tránh lớp biến đổi dữ liệu tốn giờ.
  - Cân nhắc gộp admin vào chính app React (đọc JSON) thay vì dựng Streamlit riêng, để không phải nuôi 2 stack FE.

### HIGH

#### R3 — Phụ thuộc chuỗi epic: benchmark & Radar là "đuôi", dồn rủi ro về cuối 48h
- **Liên quan:** FR-14/15 phụ thuộc FR-5 + FR-8 + FR-9 xong; FR-12/10/16 phụ thuộc FR-2 (JSON) xong; FR-16 phụ thuộc toàn Epic 1–6.
- **Mô tả:** Chuỗi cứng: dữ liệu(FR-1/2) → retrieval + as-of(FR-5/8/9) → benchmark(FR-14/15). Benchmark là **deliverable "wow" nhất nhưng nằm cuối chuỗi** — nếu retrieval/temporal trượt lịch, benchmark bị bóp thời gian và dễ chỉ kịp "1 cặp câu". Radar (FR-16) phụ thuộc mọi thứ → đúng vị trí stretch, nhưng dễ bị làm sớm vì hấp dẫn.
- **Mức đe dọa demo:** cao — benchmark là màn chốt pitch (SM-2).
- **Giảm thiểu:**
  - Dựng **benchmark harness sớm bằng mock** (2 cột, dữ liệu giả) song song, chỉ cắm pipeline thật vào khi FR-5/8/9 xong → tách rủi ro FE khỏi rủi ro backend.
  - RAG baseline = cùng pipeline **tắt** filter + graph-expand → chi phí gần 0, làm cùng lúc với pipeline chính (một cờ bật/tắt), không để thành việc riêng cuối cùng.
  - Cắm mốc kiểm tra giữa chặng: nếu hết ~H+30 mà FR-8/9 chưa xanh → khóa benchmark ở mức co 1 cặp câu, không cố bộ 20–30.

#### R4 — Điểm tích hợp dễ vỡ: embedding API + LLM API + wire FE↔BE + mock→real
- **Liên quan:** FR-4, FR-5 ([Đầy đủ] dense vector), NFR hiệu năng/bảo mật, addendum Hybrid Search.
- **Mô tả:** 4 điểm dễ vỡ còn lại sau khi đã cắt Neo4j/Qdrant: (a) embedding qua API (rate limit, latency, cần cache vector ingest 1 lần), (b) LLM API (chậm/lỗi giữa pitch — đã có mock/canned), (c) wire FE↔BE (CORS, khớp schema `sources`), (d) chuyển mock→real (env `VITE_API_MODE`). Cái dễ trượt âm thầm: **dense vector (FR-5 [Đầy đủ]) + RRF** — thêm embedding API + fusion là công thật, trong khi addendum tự thừa nhận "với data bé, differentiation nằm ở temporal filter, không ở embedding". Tức FR-5 mức đầy đủ tốn giờ mà **giá trị demo thấp**.
- **Mức đe dọa demo:** cao (LLM sập giữa pitch) → nhưng đã có lưới; embedding là bẫy tốn-giờ-ít-giá-trị.
- **Giảm thiểu:**
  - **Mặc định FR-5 ở mức co (BM25 + LLM)** cho toàn bộ kịch bản demo; chỉ thêm dense+RRF nếu dư giờ VÀ có câu demo cần ngữ nghĩa. Đừng để dense vector chặn đường tới hoàn thành.
  - Wire FE↔BE **thật + CORS ngay H0** với 1 câu hỏi mock để "đường ống xanh" sớm, tránh dồn tích hợp cuối.
  - Chuẩn hóa **bộ canned/cache cho đúng các câu demo chính** trước giờ pitch (NFR độ tin cậy demo) — coi là task bắt buộc, không phải nice-to-have.

#### R5 — Bẫy benchmark: rủi ro "tự dựng kịch bản để thắng" (SM-C2)
- **Liên quan:** FR-14, FR-15, SM-C2, §11 Constraints.
- **Mô tả:** Bằng chứng A dựa vào delta số; nếu dựng amendment tổng hợp, giám khảo tỉnh sẽ nghi "dàn trận". Rủi ro là toàn bộ benchmark mất uy tín nếu chỉ dựa A. Lưới B (thay thế một phần) + C (dẫn chiếu) là phòng thủ đúng — nhưng **chỉ vững nếu dữ liệu mẫu thật sự chứa 1 khoản bị bãi bỏ một phần + 1 dẫn chiếu, và baseline chạy đúng cùng pipeline chỉ tắt 2 bước**. Nếu B/C cũng là kịch bản dựng vụng, lưới an toàn rỗng.
- **Mức đe dọa demo:** cao — đây là màn chốt điểm "khác biệt".
- **Giảm thiểu:**
  - **Ưu tiên B & C hơn A.** Curate B, C từ quan hệ hand-annotate rõ ràng, dễ giải thích; đặt A là bổ sung.
  - Ghép **baseline = 1 cờ tắt filter + graph-expand** trên cùng pipeline (không viết pipeline yếu riêng) → chống cáo buộc "làm yếu giả tạo" một cách kiểm chứng được.
  - Chuẩn bị **câu trả lời trung thực** cho câu hỏi "đây có phải kịch bản dựng không": chỉ vào B/C không cần delta số + baseline cùng data.

### MEDIUM

#### R6 — Mâu thuẫn khái niệm "deterministic" vs "không hardcode" dễ bị dev hiểu nhầm
- **Liên quan:** FR-11 (xung đột), FR-16 (Radar), §11.
- **Mô tả:** PRD viết "kịch bản deterministic (không hardcode output)". Addendum đã giải thích: deterministic = *kịch bản chuẩn bị trước biết chắc kích hoạt rule*, KHÔNG phải nhét cứng output. Nhưng **định nghĩa này nằm ở addendum, không ở PRD** — dev đọc mỗi FR-11/FR-16 có thể hiểu nhầm thành "hard-code cho chắc ăn demo", làm hỏng chính điểm SM-5 (chịu ca lạ giám khảo nêu tại chỗ). Một câu chữ nhập nhằng → sai kiến trúc engine xung đột.
- **Mức đe dọa demo:** trung bình — nếu hiểu nhầm, SM-5 mất và có thể lộ "if-else" khi giám khảo thử ca mới.
- **Giảm thiểu:**
  - Nhắc rõ khi giao việc FR-11/16: **rule/traversal phải quét dữ liệu thật**; "deterministic" chỉ áp cho *việc chọn kịch bản demo*, không cho *cách tính kết quả*. Test bắt buộc: chạy được 1 ca **không xem trước**.

#### R7 — FR-11 xung đột: "rule quét thật ≥2 ca" tốn hơn vẻ ngoài
- **Liên quan:** FR-11, SM-5, Epic 4.
- **Mô tả:** "Đối chiếu điều khoản cùng chủ đề & cùng hiệu lực, cảnh báo khi giá trị số mâu thuẫn" đòi: (a) trích được giá trị số + đơn vị từ text khoản, (b) gom "cùng chủ đề" (cần nhãn topic hoặc heuristic), (c) so cùng hiệu lực. Trên tiny data vẫn phải parse số + gán topic bằng tay trong dữ liệu. Không khó về thuật toán nhưng **phụ thuộc dữ liệu được annotate topic/giá trị chuẩn** — lại đổ về R1.
- **Mức đe dọa demo:** trung bình.
- **Giảm thiểu:** annotate sẵn trường `topic` + `numeric_value`/`unit` trong JSON khoản ngay khi curate (gộp vào R1), để rule chỉ so sánh, không phải NLP trích số. Vẫn giữ "quét thật" vì rule chạy trên field annotate, không hardcode cặp kết quả.

#### R8 — FR-12 đồ thị tương tác: mức [Đầy đủ] là bẫy thời gian FE
- **Liên quan:** FR-12, SM-1.
- **Mô tả:** "bấm node xem chi tiết" + layout đẹp từ react-force-graph trên dữ liệu thật hay ngốn giờ tinh chỉnh (layout chồng chéo, sự kiện click, panel chi tiết). Giá trị chấm điểm chủ yếu ở "có đồ thị bấm được", không ở độ mượt.
- **Mức đe dọa demo:** trung bình.
- **Giảm thiểu:** đạt **mức co (đồ thị tĩnh/ảnh) trước**, coi tương tác là nâng cấp cuối. Không để một người sa lầy tinh chỉnh layout khi deliverable khác còn đỏ.

#### R9 — Chưa có FR/việc tường minh cho tài sản demo & phân công (thiếu sót thực thi)
- **Liên quan:** §6.1 (nhắc mock/canned), Open Q3/Q4, nhưng **không thành FR/checklist**.
- **Mô tả:** Các việc *bắt buộc để demo chạy* nhưng chưa được nâng thành hạng mục có chủ: (1) **bộ câu hỏi demo chính** (khớp A/B/C + câu khách hàng công khai FR-7) — `tests/evaluation/` đang trống; (2) **seed dữ liệu + JSON đồ thị** (R1); (3) **bộ canned/cache** cho câu demo; (4) **chọn ≥1 văn bản gắn nhãn công khai** cho FR-7 (Open Q4 chưa chốt); (5) **phân công theo epic + chia ca ngủ** (addendum nhắc nhưng chưa có bảng chủ sở hữu). Thiếu chủ rõ ràng → dễ rơi giữa các khe.
- **Mức đe dọa demo:** trung bình — từng việc nhỏ nhưng thiếu bất kỳ cái nào đều làm khựng pitch.
- **Giảm thiểu:** lập **checklist demo-assets có người chịu trách nhiệm** ngay H0: bộ câu hỏi, JSON seed, canned answers, văn bản công khai, bảng phân công 6 người theo epic. Đóng Open Q4 (chọn văn bản công khai) trong giờ đầu.

### LOW

#### R10 — Khung chấm chính thức chưa có (Open Q2)
- **Liên quan:** Open Q2, §7.
- **Mô tả:** Team tối ưu theo giả định "demo thật + độ mới". Nếu BTC công bố khung khác (ví dụ nặng về độ chính xác đo lường / quy mô dữ liệu), trọng số công sức lệch. Rủi ro thấp vì 6 deliverable là yêu cầu đề, khó lệch xa.
- **Giảm thiểu:** giữ nguyên ưu tiên 6 deliverable; cập nhật trọng số khi có khung, không chặn tiến độ.

#### R11 — SM-4 P95 < 15s trùng đúng timeout FE (15s)
- **Liên quan:** SM-4, NFR hiệu năng, API_CONTRACT (timeout FE 15s).
- **Mô tả:** Ngưỡng mục tiêu đúng bằng timeout FE → nếu LLM chạm ngưỡng, FE có thể cắt trước khi có phản hồi. Rủi ro thấp nhờ mock/canned, nhưng biên mỏng.
- **Giảm thiểu:** đặt mục tiêu nội bộ P95 < ~10s; dùng canned cho câu demo chính; cân nhắc nới timeout FE cho phiên demo nếu cần.

---

## 3 việc PHẢI làm ngay giờ H0

1. **Chốt & seed dữ liệu (gỡ R1 — critical path).** Người giỏi nghiệp vụ nhất bắt tay ngay: đóng băng schema JSON `{nodes, edges, effective_date, expiry_date, path, topic, numeric_value}`; curate 5–10 văn bản **có mục tiêu** đủ 1 khoản bị bãi bỏ một phần (bằng chứng B), 1 dẫn chiếu (C), ≥2 ca xung đột, và cố tìm 1 delta số thật (A) — nếu không có trong ~1–2h thì dựng amendment tổng hợp gắn nhãn trung thực. Ưu tiên B & C hơn A.

2. **Dựng "đường ống xanh" đầu-cuối bằng mock, song song với data.** Skeleton FastAPI trả `POST /api/chat` đúng contract (mock LLM) + wire FE real mode + CORS ngay, để FE↔BE thông trước khi có logic thật (gỡ R4). Đồng thời khởi động khối FE: thêm thư viện đồ thị và dựng benchmark harness 2 cột bằng dữ liệu giả (gỡ R2, R3). Không ai ngồi chờ dữ liệu.

3. **Lập checklist demo-assets + phân công 6 người theo epic, khóa kỷ luật mức co (gỡ R9, R2, R3, C-metrics).** Một bảng: chủ sở hữu từng epic, chia ca ngủ, danh sách câu hỏi demo (A/B/C + câu khách hàng công khai FR-7), bộ canned answers, văn bản gắn nhãn công khai (đóng Open Q4). Quy tắc bất di bất dịch: **mọi deliverable đạt mức co (xanh) trước, nâng cấp/hybrid/Radar sau** — không đụng Epic 7 khi Epic 1–6 chưa xong hết mức co.

---

## Tóm tắt severity

| ID | Severity | Tiêu đề | FR/§ chính |
|---|---|---|---|
| R1 | critical | Dữ liệu chưa tồn tại — critical path chặn ~1/2 FR | Open Q1, FR-1/2/8/9/11/14/16 |
| R2 | critical | FE trực quan dựng từ 0 trên starter trần | FR-10/12/13/14 + admin |
| R3 | high | Phụ thuộc chuỗi epic dồn benchmark/Radar về cuối | FR-14/15/16 ← FR-5/8/9/2 |
| R4 | high | Điểm tích hợp dễ vỡ (embedding/LLM/wire/mock→real) | FR-4/5, NFR |
| R5 | high | Bẫy benchmark "tự dựng để thắng" | FR-14/15, SM-C2 |
| R6 | medium | "deterministic" vs "không hardcode" dễ hiểu nhầm | FR-11/16, §11 |
| R7 | medium | FR-11 xung đột tốn hơn vẻ ngoài (trích số + topic) | FR-11, SM-5 |
| R8 | medium | FR-12 đồ thị tương tác — bẫy giờ FE | FR-12 |
| R9 | medium | Thiếu FR/checklist cho demo-assets & phân công | §6.1, Open Q3/Q4 |
| R10 | low | Khung chấm chính thức chưa có | Open Q2 |
| R11 | low | P95 15s trùng timeout FE 15s | SM-4, NFR |
