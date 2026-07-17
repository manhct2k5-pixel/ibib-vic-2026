---
title: "Review Rubric — PRD IBIB VIC 2026"
status: draft
created: 2026-07-17
reviewer: PRD Quality Reviewer
---

# Review Rubric — PRD: Trợ lý tra cứu văn bản ngân hàng thông minh (IBIB - VIC 2026)

## Overall Verdict

PRD này **mạnh hơn mức trung bình rõ rệt cho một hackathon 48h**: nó có thesis sắc (đồ thị tri thức có chiều thời gian là tài sản, không phải cái filter), gần như mọi FR đều có consequence kiểm thử được, và bộ counter-metric (SM-C1..3) chống lại đúng ba cách một team dễ tự bắn vào chân (đánh bóng stretch, làm yếu baseline, phồng scope). Điểm yếu chính không nằm ở nội dung mà ở **cơ học downstream**: có glossary/ID drift ("SUPERSEDED_BY" vs "SUPERSEDES"/"Thay thế"), vài consequence còn dựa vào tính từ mềm ("phù hợp", "hợp lý"), và một số cross-ref (API_CONTRACT.md, "bảng mức-co-tối-thiểu") trỏ ra ngoài PRD khiến một vài section không hoàn toàn đứng riêng được. Không có lỗi critical; các sửa đều nhẹ và cục bộ.

---

## 1. Decision-readiness — [adequate]

- **[low]** Quyết định lớn nằm ở brief/addendum, PRD chỉ hưởng thụ (§0, §5) — PRD tuyên bố "chi tiết *cách xây* ... nằm ở addendum ... không lặp lại ở đây". Điều này đúng shape (PRD nói năng lực), nhưng khiến các trade-off *kỹ thuật* (bỏ Neo4j/Qdrant, hand-annotate) chỉ hiện diện gián tiếp qua Non-Goals §5. *Fix:* trong §5 thêm một câu nêu rõ *cái gì bị đánh đổi* khi chọn in-memory/hand-annotate (đánh đổi khả năng scale + auto-extract lấy tốc độ tích hợp), để người đọc PRD-only vẫn thấy trade-off chứ không chỉ thấy "không làm X".
- **[low]** Open Questions thật sự mở và có hành động (§8) — cả 4 câu đều là câu chưa chốt được lúc viết (bộ dữ liệu, khung chấm, vừa-giờ-không, danh sách công khai), không phải câu tu từ. Đây là điểm mạnh. *Fix:* Q3 ("6 deliverable có vừa 48h không") nên gắn một tiêu chí quyết định (ví dụ "nếu H+24 chưa xong Epic 1–2 thì kích hoạt mức co toàn bộ") để nó là quyết định-được chứ chỉ nêu rủi ro.

## 2. Substance over theater — [strong]

- **[low]** Persona có sức nặng, không làm cảnh (§2.3) — Hà/Nam/Linh/Tú mỗi người gắn với một FR/UJ cụ thể và một nỗi sợ thật ("sợ nhất là dùng nhầm bản đã bị sửa"), không phải nhân vật trang trí. Innovation (Radar, §4.7) bị **chủ động hạ cấp** thành stretch kèm counter-metric SM-C1 — ngược với thói "phồng innovation". Vision (§1) neo vào cơ chế thật (khoảng hiệu lực + quan hệ cấp khoản), không sáo. Không có finding nghiêm trọng. *Fix:* không bắt buộc.

## 3. Strategic coherence — [strong]

- **[low]** Thesis rõ và xuyên suốt (§1, §4.6, §7) — luận điểm "differentiation nằm ở đồ thị temporal, không ở cái WHERE" được phát biểu ở Vision và **được validate** bởi SM-2 (đa bằng chứng) + FR-15 (bằng chứng B/C không cần số đổi). Ưu tiên feature khớp thesis: Epic 3 (temporal) là "lõi khác biệt", Radar bị đẩy xuống stretch. *Fix:* không bắt buộc.
- **[medium]** Counter-metric tốt nhưng SM-2 validate hơi quá tải (§7) — SM-2 khai "Validates FR-14, FR-15, FR-8, FR-9" (4 FR), trong khi SM-3 cũng ôm FR-8, FR-9. Điều này làm mờ FR nào thực sự do metric nào canh. *Fix:* tách rành mạch: để SM-2 canh differentiation (FR-14/FR-15) và SM-3 canh correctness (FR-8/FR-9), tránh chồng lấn FR-8/9 ở cả hai.

## 4. Done-ness clarity — [adequate]

- **[high]** Consequence dựa vào tính từ mềm ở các FR then chốt (§4.2 FR-4, §10 NFR) — FR-4 ghi "lỗi trả **HTTP phù hợp** + `detail`"; NFR Bảo mật ghi "CORS tới địa chỉ FE" nhưng không nói mã lỗi/loại nào. "Phù hợp" không kiểm thử được — downstream story sẽ phải tự đoán. *Fix:* thay bằng bảng cụ thể (ví dụ: câu hỏi rỗng → 422; LLM lỗi → 503 + `detail`), hoặc trỏ thẳng tới trạng thái liệt kê trong API_CONTRACT.md.
- **[medium]** "Cùng chủ đề" trong FR-11 chưa có định nghĩa kiểm thử được (§4.4) — consequence dựa vào "các Điều khoản **cùng chủ đề** & cùng hiệu lực", nhưng "cùng chủ đề" là phán đoán, không có tiêu chí (cùng metric? cùng tag?). Đây là FR "chạy thật" quan trọng cho SM-5. *Fix:* định nghĩa "cùng chủ đề" theo dữ liệu (ví dụ: hai Clause có cùng `topic_tag`/cùng loại chỉ số) để rule và test có ranh giới rõ.
- **[medium]** "Câu hỏi khách hàng demo" thiếu điều kiện quan sát được ở FR-7 (§4.2) — consequence "trả lời chỉ từ dữ liệu công khai, **không lộ Văn bản nội bộ**" đúng hướng nhưng cách *chứng minh* không-lộ chưa nêu (kiểm gì để biết không lộ?). *Fix:* thêm consequence kiểm thử: "mọi phần tử `sources` của câu hỏi ở chế độ khách hàng đều có `visibility=public`".
- **[low]** Phần lớn FR đạt chuẩn (§4 toàn cục) — đa số consequence là điều kiện nhị phân kiểm được ("Không có chunk nào cắt ngang giữa một Khoản", "`expiry_date <= asOf` không xuất hiện", "Không có câu trả lời thành công nào thiếu nguồn"). Đây là điểm mạnh của dimension khắt khe nhất. *Fix:* không bắt buộc.

## 5. Scope honesty — [strong]

- **[low]** Non-Goals + [ASSUMPTION] + [NOTE FOR PM] đặt đúng chỗ (§5, §6.2, §9) — Non-Goals cụ thể và phòng thủ ("không dựng Neo4j/Qdrant", "chỉ 5–10 văn bản"); [NOTE FOR PM] ở §6.2 cảnh báo đúng cạm bẫy stakes ("chỉ làm Radar sau khi Epic 1–6 chạy"). Open-items (4 Open Questions + 5 Assumptions) cân xứng với stakes hackathon — không quá ít (che giấu) cũng không quá nhiều (tê liệt). *Fix:* không bắt buộc.
- **[low]** [NON-GOAL for MVP] lồng trong consequence của FR-16 (§4.7) — cách đặt non-goal *bên trong* một FR (thay vì ở §5) hơi lệch chỗ, dễ bị story creation bỏ sót. *Fix:* nhân bản dòng này lên §6.2 (đã có "Máy Dò Lệch Chuẩn..." ở đó — chỉ cần chắc chắn nhất quán).

## 6. Downstream usability — [adequate]

- **[high]** Glossary drift ở edge quan hệ thay thế (§3 vs §4.1 vs addendum) — Glossary định nghĩa "Thay thế một phần (Partial supersession)" và edge khái niệm là "Thay thế"; nhưng FR-2/FR-10 dùng định danh `SUPERSEDED_BY` (§4.1, §4.3), còn addendum schema dùng `SUPERSEDES` (edge) và `SUPERSEDED_BY` (mô tả cơ chế). Ba biến thể cho cùng một quan hệ sẽ khiến architecture/story lẫn tên cạnh. *Fix:* chốt một tên cạnh chuẩn (đề nghị `SUPERSEDES` như schema addendum) và ghi chú trong Glossary rằng `SUPERSEDED_BY` là hướng nghịch của cùng cạnh — dùng nhất quán trong PRD.
- **[medium]** Một số section không đứng riêng được vì trỏ ra ngoài PRD (§4, §0) — "khớp bảng mức-co-tối-thiểu ở brief addendum" (§4), "đúng `API_CONTRACT.md`" (FR-4/§4.2), "chi tiết ở brief addendum" (§5) — người đọc chỉ có PRD không giải được các mức [Mức co]/[Đầy đủ] hay contract. *Fix:* hoặc nội tuyến bảng mức co (ít nhất cột tên deliverable + mức co một dòng) vào §6, hoặc thêm mục "Tham chiếu ngoài" liệt kê đường dẫn chính xác để cross-ref giải được.
- **[low]** ID liên tục & UJ có nhân vật tên (§2.3, §4, §7) — FR-1..16 liên tục không nhảy số; UJ-1..4 đều có nhân vật tên (Hà, Nam, Linh, Tú); SM Validates trỏ đúng FR tồn tại. Cross-ref FR↔UJ giải được (UJ-1→FR-8, UJ-2→FR-9, UJ-3→FR-7, UJ-4→FR-16). Đây là điểm mạnh. *Fix:* không bắt buộc.
- **[low]** "SM validates FR" một chiều — chưa có FR nào ngược lại trỏ tới SM, nhưng ở quy mô này chấp nhận được. *Fix:* không bắt buộc.

## 7. Shape fit — [strong]

- **[low]** Hình dạng khớp sản phẩm chain-top chấm-demo (§0, §4, §7) — tổ chức theo 7 epic tầng build + FR toàn cục + SM theo tiêu chí thi là đúng cho một PRD feeds architecture→epics. Mức co/đầy đủ hai tầng là formalization *vừa đủ* cho hackathon (không over-engineer). Không over/under-formalized. *Fix:* không bắt buộc.
- **[low]** NFR gọn, không phồng doanh nghiệp (§10) — 5 NFR (hiệu năng, bảo mật nhẹ, độ tin cậy demo, ngôn ngữ, provenance) đúng mức stakes; không đòi SLA/uptime/compliance doanh nghiệp. Phù hợp calibration. *Fix:* không bắt buộc.

---

## Mechanical Notes

**Glossary drift**
- Quan hệ "thay thế" có **3 định danh**: Glossary "Thay thế / Partial supersession" (§3), FR dùng `SUPERSEDED_BY` (§4.1 FR-2, §4.3 FR-10), addendum schema dùng `SUPERSEDES` (edge). → cần một tên cạnh chuẩn. (Xem §6 finding [high].)
- "Hybrid search" định nghĩa ở §3 = "từ khóa + ngữ nghĩa + duyệt đồ thị"; FR-5 (§4.2) hiện thực đúng nghĩa này — nhất quán. OK.
- "RAG baseline" định nghĩa §3 = "tắt lọc hiệu lực và duyệt dẫn chiếu"; FR-14 (§4.6) và SM-C2 (§7) dùng đồng nhất — nhất quán. OK.

**ID continuity**
- FR-1 → FR-16: liên tục, không trùng, không nhảy. OK.
- UJ-1 → UJ-4: liên tục; mỗi UJ được "Hiện thực hóa" bởi ít nhất một Epic (Epic1→UJ-4, Epic2→UJ-1/3, Epic3→UJ-1/2, Epic7→UJ-4). OK.
- SM-1..5 + SM-C1..3: đánh số nhất quán; mọi "Validates FR-N" đều trỏ tới FR tồn tại. OK.
- Deliverable đề (6) ↔ Epic (1–6) ↔ FR: ánh xạ giải được qua nhãn *(deliverable: ...)* trên FR-3/6/10/11/12/14. OK.

**Assumptions Index roundtrip (§9)**
- [GIẢ ĐỊNH] §1/§7 (ưu tiên chấm = khả thi + độ mới) → khớp §1, §7, và brief "Tiêu chí thành công". ✓ roundtrip.
- [GIẢ ĐỊNH] §6.1 (5–10 văn bản đủ phủ 4 tình huống) → khớp §6.1 In Scope. ✓
- [GIẢ ĐỊNH] §4.2 FR-4 (giữ contract `/api/chat`) → khớp FR-4. ✓
- [GIẢ ĐỊNH] §4.7 (Radar 1 kịch bản deterministic đủ ăn điểm) → khớp §4.7 FR-16. ✓
- [GIẢ ĐỊNH] §2.1 (khách hàng thứ cấp, một khoảnh khắc demo) → khớp §2.1 và §2.3 UJ-3. ✓
- **Không có** assumption nào trỏ tới section không tồn tại; **không có** assumption mồ côi. Roundtrip sạch. Chỉ thiếu: rủi ro H0 (bộ dữ liệu/bẫy số) sống ở Open Questions §8.1 nhưng **không** được mirror thành một [GIẢ ĐỊNH] — cân nhắc thêm để Assumptions Index phản ánh giả định "sẽ dựng được amendment tổng hợp trung thực".

**Two-tier co/đầy-đủ**
- Các nhãn [Mức co]/[Đầy đủ] xuất hiện ở FR-3, FR-5, FR-8, FR-10, FR-11, FR-12, FR-14; tất cả tuyên bố "khớp bảng mức-co-tối-thiểu ở brief addendum" (§4). Bảng đó **có tồn tại** trong addendum (6 dòng) — cross-ref giải được *nếu* người đọc có addendum. Với PRD-only reader thì không. (Xem §6 finding [medium].)
