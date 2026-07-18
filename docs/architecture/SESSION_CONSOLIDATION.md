# Văn bản hợp nhất & Phân tích quan hệ — THIẾT KẾ MVP (session-only)

> Ghi chú kiến trúc — chốt ngày 2026-07-18 theo yêu cầu chủ dự án.

## Nguyên tắc cốt lõi (MVP hiện tại)

**Tính năng "văn bản hợp nhất" và "bản đồ quan hệ / hướng dẫn đọc" CHỈ dùng dữ
liệu từ FILE NGƯỜI DÙNG UPLOAD trong phiên. KHÔNG liên quan tới database.**

- Mỗi lần người dùng đính kèm tài liệu → hệ thống **dựng lại dữ liệu từ chính các
  file đó** (cắt Điều/Khoản, trích metadata, suy quan hệ liên-văn-bản) rồi phân
  tích. Không đọc, không ghi, không đối chiếu với PostgreSQL/DWH.
- Toàn bộ dữ liệu phiên là **ephemeral, in-memory theo `sessionId`** (AD-13),
  không persist, mất khi hết phiên/restart.
- Tích hợp với database (dùng corpus/quan hệ đã seed trong DWH) là **PATCH PHÁT
  TRIỂN SAU** — chưa nằm trong phạm vi MVP này. Đừng trộn hai luồng.

## Luồng dữ liệu (chỉ từ file upload)

1. **Upload** (`POST /api/session/upload-pdf`) — NHANH, không gọi LLM:
   - `extract_text`: đọc lớp text PDF; nếu PDF scan/font hỏng (không có "Điều")
     → fallback **OCR tiếng Việt** (pypdfium2 render + tesseract `vie`, chạy song
     song trang).
   - `quick_metadata` (regex): suy `doc_code` (ưu tiên TÊN FILE) + ngày hiệu lực.
   - Cắt Điều → `SessionClause`; lưu `SessionDoc(raw_text, analyzed=False)`.
2. **Gửi câu hỏi** → `POST /api/session/analyze` — chạy LLM TRỄ:
   - Với mỗi doc chưa phân tích: LLM trích quan hệ (AMENDS/SUPERSEDES/REFERENCES/
     CONSOLIDATES/GUIDES) + metadata đầy đủ; regex bù "Căn cứ".
   - Dựng **bản đồ quan hệ** (graph) + **thứ tự đọc** + **hướng dẫn đọc**.
3. **Văn bản hợp nhất tổng hợp** (`GET /api/session/consolidated`):
   - Chọn **MỘT** văn bản nền (`primaryDoc`): ưu tiên VBHN (đã hợp nhất) → văn bản
     bị sửa đổi/thay thế trong phiên (bản gốc) → văn bản nhiều điều nhất.
   - Gộp các sửa đổi từ những file khác trong phiên vào bản nền; đánh dấu từng
     Điều bị sửa đổi (amendedBy + note). **Chỉ 1 văn bản hợp nhất**, không tạo bản
     riêng cho từng file.

## Ranh giới (Boundaries)

- **Chỉ session:** mọi tính năng trên chỉ đọc `session_store` (docs/relations/
  clauses của `sessionId`). KHÔNG gọi `KnowledgeBase`/DWH.
- **Endpoint DB tách biệt:** `GET /api/consolidate` (hợp nhất theo corpus DWH) và
  phần retrieve DB trong `/api/chat` là luồng KHÁC — không phải tính năng này.
  Tránh nhầm hai luồng khi demo/giải thích.
- **Không persist:** không ghi tài liệu phiên vào bảng global.

## File liên quan (backend)

- `kb/session_store.py` — SessionDoc/SessionRelation/SessionClause (in-memory).
- `ingest/pdf_ingest.py` — extract_text (+OCR fallback), cắt Điều.
- `ingest/doc_analyze.py` — quick_metadata (regex) + analyze_document (LLM).
- `pipeline/session_analyze.py` — build_session_analysis, pick_primary_doc,
  build_session_consolidated.
- `api/main.py` — `/api/session/{upload-pdf, analyze, analysis, consolidated,
  doc(DELETE)}`.

## Phương pháp xây dựng văn bản hợp nhất (chuẩn — chốt 2026-07-18)

Quy trình mục tiêu 5 bước (tham chiếu nghiệp vụ Pháp chế):

1. **Phát hiện quan hệ sửa đổi** (cross-reference tự động): AI đọc văn bản mới,
   nhận diện "sửa đổi Điều 5", "bổ sung khoản 2 Điều 10", "thay thế toàn bộ
   Chương III" → gắn quan hệ vào đồ thị tri thức.
   - *Hiện trạng:* ĐÃ CÓ ở mức văn bản + Điều (`doc_analyze` LLM trích AMENDS/
     SUPERSEDES + `target_article`). TODO: xuống mức Khoản/Chương.
2. **Tách văn bản gốc thành đơn vị nhỏ nhất (clause-level)**: không hợp nhất cả
   văn bản, tách theo từng Điều/Khoản để biết chính xác điều nào bị thay, điều nào
   giữ nguyên (clause-level supersession tracking).
   - *Hiện trạng:* ĐÃ CÓ cắt theo Điều. TODO: cắt xuống Khoản.
3. **Sinh bản hợp nhất nháp (AI draft)**: ghép văn bản gốc còn hiệu lực + các điều
   khoản sửa đổi mới nhất → 1 bản đọc liền mạch; **mỗi điều khoản có trace-back**
   (footnote: "điều này lấy từ Quyết định số… ngày…"). Nguyên tắc pháp lý: KHÔNG
   thay đổi giá trị hiệu lực gốc, chỉ hỗ trợ tra cứu.
   - *Hiện trạng:* ĐÃ CÓ bản hợp nhất quanh 1 văn bản nền + đánh dấu amendedBy.
     TODO: footnote trace-back đầy đủ (số/ngày văn bản nguồn) + nội dung điều sửa.
4. **Human-in-the-loop review (BẮT BUỘC)**: văn bản hợp nhất KHÔNG có giá trị pháp
   lý độc lập → bản AI chỉ là **nháp hỗ trợ Pháp chế**, không tự động ban hành.
   Cần **Admin dashboard** hiển thị **diff trực quan** (phần AI thêm/sửa) để Pháp
   chế duyệt nhanh trước khi công bố nội bộ.
   - *Hiện trạng:* CHƯA — thuộc patch admin/DB sau (gắn với luồng approve DWH).
5. **Timeline & overview tổng quan**: văn bản gốc → các lần sửa đổi → bản hợp nhất
   hiện tại, tránh sót lần sửa nào (knowledge version timeline).
   - *Hiện trạng:* CÓ thứ tự đọc + bản đồ quan hệ session; timeline theo phiên bản
     đầy đủ = TODO (gắn version timeline).

## TODO (patch sau — DB integration)

- Đối chiếu tài liệu upload với corpus DWH đã seed (khi văn bản đích không được
  upload, tra trong DB để hoàn thiện bản hợp nhất/quan hệ).
- Gộp article-level chính xác hơn (lấy nội dung điều sửa đổi từ văn bản sửa đổi).
- Hợp nhất tên node trùng (vd `VB39-2016` ↔ `TT39`).
