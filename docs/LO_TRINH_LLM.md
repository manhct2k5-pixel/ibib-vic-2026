# Lộ trình ứng dụng LLM — Compliance Copilot

> Định hướng đưa LLM sâu hơn vào các quy trình để hệ thống mượt & thông minh hơn.
> Cập nhật: 2026-07-19.

---

## 1. Hiện trạng sử dụng LLM

| Quy trình | Hiện tại | Có LLM? |
|---|---|---|
| Phân tích tài liệu upload (quan hệ + metadata) | LLM trích JSON (`doc_analyze.py`) | ✅ |
| Trả lời chat (`run_pipeline`) | BM25 + ghép template (liệt kê điều khoản thô) | ❌ |
| Tìm kiếm (retrieve) | BM25 (từ khóa); cột vector dùng **embedding giả (hash)** | ❌ |
| Hợp nhất văn bản | Rule-based, đánh dấu mức Điều | ❌ |
| Hướng dẫn đọc | Rule-based (ghép câu) | ❌ |
| Phát hiện xung đột | Rule-based (so số liệu) | ❌ |
| OCR | tesseract, không hậu xử lý | ❌ |

**Nhận định:** LLM mới dùng ở 1 điểm. Nhiều quy trình rule-based nên kết quả còn
thô (điển hình: câu trả lời chat là "bức tường chữ" liệt kê nguyên văn điều khoản).

---

## 2. Các hướng cải thiện

### 🔴 Ưu tiên cao — tác động lớn, đúng gốc vấn đề

#### #1. LLM tổng hợp câu trả lời chat (RAG synthesis) — QUAN TRỌNG NHẤT
- **Hiện tại:** `run_pipeline` không dùng LLM → câu trả lời chỉ là danh sách text
  điều khoản thô (chính là lý do "quá dài / khó đọc").
- **Cải thiện:** sau khi retrieve các điều khoản liên quan (đã lọc hiệu lực), đưa
  cho LLM viết câu trả lời **mạch lạc, ngắn gọn, có trích dẫn `[TT22/Điều 1]`**,
  bám đúng câu hỏi. Đây là bước "synthesize" đúng nghĩa của RAG.
- **Vị trí:** `pipeline/pipeline.py` (đã có sẵn `providers/llm.py` + `synthesize.py`
  chưa dùng). Có fallback MockLLM khi thiếu key.
- **Lợi ích:** trả lời tự nhiên như trợ lý thật; giảm độ dài; vẫn trích nguồn.
- **Công sức:** vừa. **Rủi ro:** cần kiểm soát "bịa" — chỉ cho LLM dùng điều khoản
  được cung cấp (grounded), yêu cầu trích dẫn.

#### #2. Tìm kiếm ngữ nghĩa (embedding thật) — thay/bổ sung BM25
- **Hiện tại:** cột vector `dwh.anh_xa` dùng **embedding hash giả** → vô dụng;
  retrieve chỉ dựa BM25 (khớp từ khóa, yếu với câu hỏi diễn giải khác từ).
- **Cải thiện:** dùng **embedding model thật** (API hoặc model local tiếng Việt) để
  tìm theo nghĩa; kết hợp **hybrid** BM25 + vector.
- **Vị trí:** `kb/vector_helper.py` (thay `get_text_embedding`), `pipeline` retrieve.
- **Lợi ích:** hỏi "vốn đệm an toàn tối thiểu" vẫn ra điều khoản CAR dù không có
  từ "CAR"; tăng recall đáng kể.
- **Công sức:** vừa–cao (cần chọn model + reindex embedding cho corpus).

### 🟠 Ưu tiên trung bình — nâng chất lượng nghiệp vụ

#### #3. Hợp nhất mức điều khoản + trace-back bằng LLM (Bước 3 quy trình hợp nhất)
- **Hiện tại:** hợp nhất chỉ đánh dấu "Điều X bị TT06 sửa" ở mức văn bản.
- **Cải thiện:** LLM đọc điều gốc + nội dung sửa đổi → **sinh text điều khoản đã
  hợp nhất** kèm **footnote trace-back** ("nội dung theo TT06/2023 sửa Điều 22
  TT39"). Có thể xuống mức Khoản/Điểm.
- **Vị trí:** `pipeline/session_analyze.py` (`build_session_consolidated`).
- **Lợi ích:** đúng bản chất "văn bản hợp nhất" đọc liền mạch, không chỉ đánh dấu.
- **Lưu ý pháp lý:** bản AI sinh ra là **nháp hỗ trợ**, cần Pháp chế duyệt (Bước 4).

#### #4. Hiểu & viết lại câu hỏi (query understanding)
- **Cải thiện:** LLM phân tích câu hỏi trước khi retrieve: trích **chủ đề, loại văn
  bản, mốc thời gian ngụ ý, ý định** (tra cứu / so sánh / "có gì thay đổi") → viết
  lại truy vấn + chọn nhánh xử lý.
- **Vị trí:** thêm stage đầu `pipeline/pipeline.py`.
- **Lợi ích:** hỏi "quy định cho vay 2020 khác gì bây giờ" → tự hiểu là so sánh 2 mốc.

#### #5. Làm sạch OCR bằng LLM
- **Hiện tại:** OCR còn lỗi ("l1 tháng I1" = "11 tháng 11", "só" = "số").
- **Cải thiện:** LLM hậu xử lý text OCR (sửa lỗi chính tả/số) trước khi cắt Điều.
- **Vị trí:** `ingest/pdf_ingest.py` (sau `_ocr_pdf`).
- **Lợi ích:** metadata & hợp nhất chính xác hơn. **Lưu ý:** tốn thêm 1 lượt LLM/tài liệu.

### 🟡 Ưu tiên thấp — bổ sung trải nghiệm

#### #6. Giải thích xung đột + gợi ý áp dụng
- Khi phát hiện xung đột (NHNN 9% vs nội bộ 10%), LLM **giải thích** văn bản nào ưu
  tiên áp dụng và vì sao. Vị trí: `pipeline/pipeline.py` (`conflict_check_stage`).

#### #7. Tự gắn topic + trích số liệu cho clause upload
- LLM gắn `topic` + trích `metric_value/unit` cho tài liệu upload → bật được **phát
  hiện xung đột trên chính tài liệu người dùng**. Vị trí: `ingest/doc_analyze.py`.

---

## 3. Bảng tổng hợp ưu tiên

| # | Hướng | Tác động | Công sức | Ưu tiên |
|---|---|---|---|---|
| 1 | LLM synthesize câu trả lời | ★★★ | ★★ | 🔴 Làm trước |
| 2 | Embedding ngữ nghĩa (hybrid) | ★★★ | ★★★ | 🔴 |
| 3 | Hợp nhất mức điều + trace-back | ★★ | ★★★ | 🟠 |
| 4 | Query understanding | ★★ | ★★ | 🟠 |
| 5 | Làm sạch OCR | ★★ | ★ | 🟠 |
| 6 | Giải thích xung đột | ★ | ★ | 🟡 |
| 7 | Auto topic/metric cho upload | ★ | ★★ | 🟡 |

---

## 4. Lộ trình đề xuất

1. **Giai đoạn 1 (nền tảng trả lời):** #1 LLM synthesize → #5 làm sạch OCR (rẻ, cải
   thiện toàn bộ downstream).
2. **Giai đoạn 2 (tìm kiếm thông minh):** #2 embedding hybrid → #4 query understanding.
3. **Giai đoạn 3 (chất lượng hợp nhất):** #3 hợp nhất mức điều + trace-back → #7 auto
   topic/metric → #6 giải thích xung đột.

---

## 5. Nguyên tắc khi áp LLM (để an toàn & ổn định)
- **Grounded:** chỉ cho LLM dùng dữ liệu được cung cấp; bắt buộc trích nguồn; không
  bịa số liệu/điều khoản.
- **Fallback:** mọi lời gọi LLM phải có đường lui (MockLLM / rule-based) khi lỗi/timeout.
- **Chi phí & độ trễ:** cache kết quả phân tích; gọi LLM ở bước cần thiết (đã áp dụng
  nguyên tắc "phân tích khi Gửi").
- **Pháp lý:** đầu ra AS liên quan văn bản hợp nhất là **nháp hỗ trợ**, cần con người
  (Pháp chế) duyệt — không tự động ban hành.
