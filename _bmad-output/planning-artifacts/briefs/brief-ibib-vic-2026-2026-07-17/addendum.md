---
title: "Addendum: Trợ lý tra cứu văn bản ngân hàng thông minh"
status: draft
created: 2026-07-17
updated: 2026-07-17
---

# Addendum — Chiều sâu kỹ thuật & bối cảnh

Tài liệu bổ trợ cho `brief.md`. Chứa chi tiết dành cho bước PRD/Architecture, không nằm trong brief để giữ brief gọn 1–2 trang.

## Nguyên tắc kỹ thuật cho hackathon 48h

> ⚠️ **CẬP NHẬT (đã đổi):** Lớp dữ liệu chuyển từ **in-memory (NetworkX + rank_bm25 + JSON)** sang **PostgreSQL** (bảng documents/clauses/edges + full-text + thời gian), truy cập qua **tầng repository** (Architecture Spine AD-2/AD-7/AD-12). Database do **Epic 0 (người khác phụ trách)**. Các đoạn nói "NetworkX/BM25/in-memory" bên dưới là **bối cảnh lịch sử** — quyết định hiện hành là Postgres. `corpus.json` vẫn là hạt giống (seed) nạp vào DB.

Bài toán demo là **tiny data**: 5–10 văn bản cắt theo Điều/Khoản ≈ vài trăm chunk. Ở quy mô đó, mọi hạ tầng "for scale" đều là rủi ro tích hợp thừa. Ba quyết định chốt:

- **Không dùng graph DB (Neo4j).** Đề bài tự gợi ý "Neo4j **/ NetworkX**" — chọn NetworkX in-memory, serialize ra JSON `{nodes, edges}`. JSON đó vừa nuôi trực quan đồ thị (react-force-graph), vừa dùng để traverse dẫn chiếu. Một cấu trúc phục vụ cả hai deliverable, không phải học Cypher dưới áp lực.
- **Không dựng vector DB server (Qdrant).** Vài trăm vector → numpy cosine là tức thì; nếu muốn tiện dùng ChromaDB **nhúng (in-process)**, tuyệt đối không dựng server riêng.
- **Không auto-extract quan hệ từ PDF luật thô.** Trích quan hệ thời gian tiếng Việt tự động là bài toán tự nó đủ đốt sạch 48h. Với 5–10 doc, **hand-annotate** cạnh AMENDS/SUPERSEDES/REFERENCES trong JSON. Chỉ build parser nếu còn dư thời gian.

Cắt được vector DB + graph DB là bỏ hai điểm tích hợp dễ vỡ nhất. Stack còn lại gọn: FastAPI + rank_bm25 + embeddings + dict/JSON graph (NetworkX) + React + LLM API.

## Kiến trúc tổng thể (5 tầng)

1. **Nguồn đầu vào:** văn bản ngoài (SBV, Chính phủ, Basel) + văn bản nội bộ (SOP, hợp đồng, chính sách).
2. **Versioning Engine (offline):** Parse PDF/DOCX → chunking theo cấu trúc Điều/Khoản/Điểm → trích metadata (loại VB, cơ quan, ngày ban hành/hiệu lực) → gắn quan hệ (SỬA ĐỔI / THAY THẾ / DẪN CHIẾU / HƯỚNG DẪN) **bằng tay vào JSON** → gắn khoảng hiệu lực [ngày bắt đầu, ngày hết hạn).
3. **Bộ nhớ lõi:** BM25 + dense vector (nội dung chunk, in-memory/nhúng) song song với đồ thị NetworkX (quan hệ + thời gian), nạp từ 1–2 file JSON lúc startup.
4. **Tầng trí tuệ:** Hỏi–đáp có trích nguồn, Bộ phát hiện xung đột (bắt buộc); Radar Tác động (mở rộng — điểm sáng tạo); Văn bản Hợp nhất Sống, Máy Dò Lệch Chuẩn (nếu còn thời gian).
5. **Giao diện:** khung chat + trích nguồn, đồ thị tri thức, timeline phiên bản, banner xung đột, màn admin/ingest, báo cáo tác động.

## Đồ thị tri thức — schema đề xuất

Lưu trong NetworkX, serialize ra JSON để cả FE lẫn backend dùng chung.

**Nodes**
- `Document` — {id, type (Luật/NĐ/TT/Basel), issuer, issue_date, effective_date, expiry_date, status}
- `Clause` (Điều/Khoản/Điểm) — {id, doc_id, path ("Điều 5.3"), text, effective_date, expiry_date, status (active/superseded/expired)}

**Edges**
- `AMENDS` (sửa đổi) — cấp khoản
- `SUPERSEDES` (thay thế, full/partial)
- `REFERENCES` (dẫn chiếu)
- `GUIDES` (hướng dẫn thi hành)
- `CONFLICTS_WITH` (phát hiện được)

## Cơ chế giải quyết 4 năng lực khác biệt đề bài yêu cầu

- **Sửa đổi & thay thế một phần → "as-of date filtering":** khi nạp văn bản sửa đổi, tạo version node mới, nối `old -[SUPERSEDED_BY]-> new`, set `old.expiry_date = new.effective_date`. Truy vấn lọc `effective_date <= asOf < expiry_date` (mặc định asOf = hôm nay).
  - *Tách bạch hai chuyện, đừng lẫn:* **chi phí xây** của bước lọc gần như bằng 0 (một câu WHERE) — tốt cho tiến độ, **bảo vệ bằng mọi giá**. Nhưng **khi pitch tuyệt đối không bán "cái filter"**, vì giám khảo tỉnh sẽ hỏi "lọc theo ngày thì AI ở đâu?". Thứ đáng bán là **tài sản mà filter đọc lên**: đồ thị điều khoản có phiên bản ở cấp khoản, dựng lại được trạng thái luật tại mọi thời điểm (as-of reconstruction), xử được *thay thế một phần* (loại đúng khoản bị bãi bỏ, giữ phần còn hiệu lực). Đó mới là 2/4 năng lực đề nêu và là phần công sức thật.
- **Dẫn chiếu chéo → graph traversal:** cạnh REFERENCES gắn tay; khi retrieve thì graph-expand 1–2 hop trên NetworkX. (Citation parser regex là tùy chọn, không phải điểm "wow".)
- **Xung đột → rule quét thật, ≥2 ca (không hardcode output):** thiết kế 2 tầng — (1) rule **duyệt dữ liệu** so sánh giá trị số của các khoản cùng chủ đề & cùng hiệu lực; (2) LLM judge cặp điều khoản tương đồng để giảm false positive. **Làm rõ để không tự mâu thuẫn:** "deterministic" ở đây nghĩa là *kịch bản chuẩn bị trước biết chắc sẽ kích hoạt rule*, KHÔNG phải *nhét cứng câu trả lời*. Ship **≥2 ca** và để rule chạy thật trên data, sao cho nó xử được cả một ca giám khảo tự nghĩ ra tại chỗ — đó là khác biệt giữa "chạy thật" và "if-else". Engine phát hiện xung đột tổng quát (mọi loại mâu thuẫn) vẫn là stretch, không phải MVP.

## Hybrid Search

| Thành phần | Vai trò | Công cụ (chốt cho 48h) |
|---|---|---|
| BM25 | khớp từ khóa/số điều/số VB | rank_bm25 (in-memory) |
| Dense vector | ngữ nghĩa tiếng Việt | multilingual-e5-large hoặc bge-m3 — **gọi qua API để khỏi phụ thuộc GPU**; ingest 1 lần, query 1 vector |
| Graph traversal | mở rộng theo dẫn chiếu | NetworkX (in-memory) |
| Fusion | gộp kết quả | Reciprocal Rank Fusion (RRF) |

**Quan trọng:** chunking theo cấu trúc pháp lý (Điều/Khoản/Điểm), KHÔNG theo token cố định.

_Lưu ý phạm vi giá trị:_ với data bé, differentiation nằm ở **temporal filter** chứ không ở chất lượng retrieval. Về lý thuyết có thể demo cái bẫy chỉ với BM25 + LLM; giữ hybrid cho robust, nhưng biết rủi ro/giá trị không nằm ở khâu embedding.

## Tech stack đề xuất (đã chốt cắt giảm)

- Backend: **FastAPI** (thư mục `backend/` đang trống) — expose `POST /api/chat` đúng `docs/architecture/API_CONTRACT.md`.
- Frontend: React starter đã có; bổ sung hiển thị nguồn trích, timeline phiên bản, banner xung đột, đồ thị (react-force-graph / vis-network).
- Lớp dữ liệu: **PostgreSQL 17 + psycopg 3** qua `kb/repository.py` (KHÔNG Neo4j/Qdrant/NetworkX). Quan hệ = bảng `edges` + recursive CTE; tìm kiếm = full-text `ts_rank`.
- Vector store: chưa dùng cho MVP (Deferred).
- LLM: Claude / GPT-4 qua API (key chỉ ở backend).
- Admin/ingest: Streamlit.

## Kế hoạch demo (ưu tiên chạy thật)

Sáu deliverable đều bắt buộc nhưng **không cùng độ khó**, nên trong lớp must vẫn có thứ tự nội bộ và **mức co tối thiểu** (nếu cháy giờ, co lại chứ không bỏ trống — thà 6 thứ chỉn chu mức tối thiểu còn hơn 6 thứ dở dang). Xây theo đúng thứ tự này, mỗi mục đạt "mức co" trước rồi mới nâng cấp:

| # | Deliverable | Mức co tối thiểu (nếu cháy giờ) | Bản đầy đủ |
|---|---|---|---|
| 1 | Chatbot + trích nguồn qua `/api/chat` | Trả lời + citation text | + as-of, + graph-expand |
| 2 | Temporal filter (as-of) | Filter mặc định = hôm nay | + chọn as-of quá khứ trên UI |
| 3 | Benchmark vs RAG thường | 1 cặp câu side-by-side | Bộ 20–30 câu, đa bằng chứng |
| 4 | Bộ phát hiện xung đột | 2 ca, rule quét thật | + LLM judge giảm false positive |
| 5 | Admin/ingest | **Đọc từ file JSON** | UI Streamlit ingest |
| 6 | Đồ thị + timeline phiên bản | Timeline = **danh sách**; đồ thị tĩnh | react-force-graph tương tác |

- **Thêm một câu hỏi khách hàng** (chế độ chỉ-dữ-liệu-công-khai) vào kịch bản chatbot — để "phục vụ cả khách hàng" không còn là lời hứa suông.

**Lớp 2 — Nâng cao (điểm sáng tạo, không nằm trong deliverable đề):**
7. Radar Tác động + màn hình báo cáo ảnh hưởng — kịch bản deterministic (chuẩn bị sẵn, không hardcode output): nạp 1 văn bản sửa đổi → liệt kê đúng khoản/văn bản bị ảnh hưởng.

**Lớp 3 — Chỉ nếu còn thời gian:**
8. Máy Dò Lệch Chuẩn, Văn bản Hợp nhất Sống.

**Màn chốt pitch (benchmark) — đa bằng chứng, không đặt hết vào cái bẫy số:**
- *Bằng chứng A (cần delta số):* "Tỷ lệ an toàn vốn tối thiểu hiện nay là bao nhiêu?" → RAG thường trả bản gốc (sai) vs ta trả bản sửa đổi mới nhất + cảnh báo. **Chỉ mạnh nếu số thật sự đổi** — xem rủi ro H0; nếu là amendment dựng thì trung thực khi trình bày.
- *Bằng chứng B (KHÔNG cần delta số):* thay thế một phần — ta loại đúng khoản đã bị bãi bỏ, RAG thường vẫn trả nó.
- *Bằng chứng C (KHÔNG cần delta số):* dẫn chiếu — ta tự kéo điều được dẫn chiếu, RAG thường bỏ sót.
- B và C là lưới an toàn: kể cả khi bẫy số bị nghi ngờ, khác biệt vẫn chứng minh được. RAG baseline chạy trên **cùng data, cùng pipeline**, chỉ tắt bước lọc hiệu lực + graph-expand.

**Phương án dự phòng khi demo sập (rất thực trong hackathon):** LLM API có thể chậm/lỗi giữa pitch. Frontend đã có mock mode. Chuẩn bị **bộ câu trả lời cache/canned cho đúng các câu demo chính**, và một câu chuyển cảnh trong kịch bản ("nếu API lag, chuyển sang bản đã ghi") để không trắng tay trên sân khấu.

## Ánh xạ với Key Deliverables của đề bài

| Deliverable đề yêu cầu | Giải pháp | Lớp |
|---|---|---|
| AI chatbot có trích nguồn | Query pipeline + citation trong prompt | Bắt buộc |
| Knowledge graph visualization | react-force-graph từ JSON (NetworkX) | Bắt buộc |
| Clause version timeline | Duyệt chuỗi SUPERSEDED_BY → render timeline | Bắt buộc |
| Conflict detector | Rule quét thật + LLM 2 tầng; ship ≥2 ca | Bắt buộc |
| Admin dashboard cập nhật VB | Streamlit ingest UI | Bắt buộc |
| Benchmark vs standard RAG | Bộ ~20–30 câu hỏi "bẫy thời gian" | Bắt buộc |
| *(ngoài đề)* Radar Tác động | Lan tỏa tác động trên đồ thị | Sáng tạo |

## Bối cảnh nhóm & tài sản sẵn có

- Nhóm IBIB (6 thành viên: Bảo, Mạnh Phan, Thúy Toàn, Yến, Chiến Thắng, Lan Anh).
- Repo đã có: frontend React/TS/Vite với 2 chế độ mock/real, `API_CONTRACT.md`, khung thư mục backend/data/tests.
- `backend/`, `data/sample/`, `tests/evaluation/` hiện trống — cần điền.

**Lưu ý nhân lực (6 người / 48h):** rủi ro giẫm chân và coordination overhead cao. Data curation là critical path — giao cho người giỏi nhất, **bắt đầu ngay giờ H0**, song song với dựng skeleton backend + wire `/api/chat` (mock LLM trước, thật sau). Đừng để cả team chờ dữ liệu. Chia ca ngủ — 48h không phải 48h thức.

## Trạng thái các câu hỏi mở

Đã chốt:
- Thời lượng thi: **48 giờ**.
- Khách hàng (thứ cấp): **có nằm trong bản demo**, giới hạn ở dữ liệu công khai.
- Con số giá trị kinh doanh: **để định tính**, không nêu số bịa. Giữ số "2–3 giờ/ngày" vì là số của đề bài SHB.
- Lớp dữ liệu: **PostgreSQL** (bảng documents/clauses/edges + full-text + thời gian) qua tầng repository — bỏ Neo4j/Qdrant *(và bỏ luôn NetworkX/in-memory ở bản cập nhật)*.
- Vector: chưa dùng (Postgres full-text cho MVP); dense là Deferred.
- Trích quan hệ: **hand-annotate JSON** (không auto-extract).

Còn treo (ưu tiên xử lý ngay giờ H0):
- **RỦI RO SỐ MỘT — Bộ văn bản demo & tính thật của cái bẫy số.** Chưa có file. Cần xác minh: có tồn tại một điều khoản mà **giá trị số bị thay đổi** bởi văn bản sau (ví dụ CAR/tỷ lệ an toàn vốn giữa TT41 và bản sửa đổi) không? Nếu dữ liệu thật không có, **dựng một amendment tổng hợp** — chấp nhận được nhưng phải trung thực rằng đó là kịch bản dựng, và số phải nhất quán trong toàn bộ mẫu.
  - *Đã có lưới an toàn:* không đặt hết vào bẫy số. Bằng chứng B (thay thế một phần) và C (dẫn chiếu) chứng minh khác biệt **không cần giá trị số đổi** — chỉ cần dữ liệu mẫu có 1 khoản bị bãi bỏ một phần và 1 quan hệ dẫn chiếu, cả hai đều hand-annotate được, không phụ thuộc luật thật. Nhờ vậy rủi ro #1 hạ từ "sụp benchmark" xuống "mất 1 trong 3 bằng chứng".
- **Rủi ro sập demo trực tiếp.** LLM API chậm/lỗi giữa pitch. Giảm thiểu: mock mode có sẵn + bộ câu trả lời cache/canned cho các câu demo chính (xem Kế hoạch demo).
- **Sáu deliverable có vừa 48h/6 người không** — chưa đánh giá được, phụ thuộc phân công thực tế. Bảng "mức co tối thiểu" ở trên là van an toàn: nếu cháy giờ thì co, không bỏ trống.
- Tiêu chí chấm điểm chính thức của ban tổ chức — **cập nhật sau**; hiện tối ưu theo 6 deliverable + hai trọng số "demo thật" và "sáng tạo".