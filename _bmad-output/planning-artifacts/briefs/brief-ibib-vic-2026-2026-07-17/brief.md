---
title: "Product Brief: Trợ lý tra cứu văn bản ngân hàng thông minh (IBIB - VIC 2026)"
status: draft
created: 2026-07-17
updated: 2026-07-17
---

# Product Brief: Trợ lý tra cứu văn bản ngân hàng thông minh

> Dự án dự thi **Vietnam AI Innovation Challenge 2026** — Đề bài SHB: *Advanced RAG Knowledge Base – AI Chatbot for Complex Banking Document Retrieval*. Nhóm **IBIB**. Thời lượng thi: **48 giờ**.

## Executive Summary

Ngân hàng SHB quản lý hàng nghìn văn bản pháp lý nội bộ và bên ngoài (SBV, Chính phủ, Basel). Chúng chồng chéo và thay đổi liên tục: một quy định có thể bị sửa đổi nhiều lần, một điều khoản có thể bị bãi bỏ một phần, và các văn bản có thể dẫn chiếu hoặc mâu thuẫn lẫn nhau. Công cụ tra cứu thông thường — kể cả RAG tiêu chuẩn — chỉ tìm đoạn văn "giống câu hỏi nhất", nên dễ trả về điều khoản đã hết hiệu lực, gây rủi ro tuân thủ và nguy cơ bị phạt.

**Trợ lý tra cứu văn bản ngân hàng thông minh** là một trợ lý pháp lý (Compliance Copilot) xây trên một **đồ thị tri thức có chiều thời gian** (Temporal Legal Knowledge Graph). Nhân viên hỏi bằng tiếng Việt tự nhiên và nhận câu trả lời đúng quy định đang có hiệu lực, kèm trích dẫn nguồn chính xác. Đề bài SHB nêu bốn năng lực khác biệt phải giải: *lần theo dẫn chiếu*, *luôn áp bản sửa đổi mới nhất*, *loại điều khoản đã bị thay thế một phần*, và *phát hiện xung đột*. Toàn bộ bốn năng lực này đều quy về một lớp lõi: đồ thị quan hệ có gắn chiều thời gian.

Đây không phải bài toán "xây một LLM mới". Giá trị nằm ở lớp tri thức pháp lý có chiều thời gian, giúp một LLM có sẵn (Claude/GPT-4) trả lời đúng luật, đúng thời điểm — điều RAG trần trụi không làm được.

## Vấn đề

Với hàng nghìn văn bản luôn biến động, nhân viên ngân hàng đối mặt bốn nỗi đau mà cả tra cứu thủ công lẫn RAG thường đều không giải được:

1. **Đọc nhầm quy định đã hết hiệu lực.** Một điều khoản đã bị sửa hoặc bãi bỏ vẫn hiện ra như còn hiệu lực, dẫn tới áp dụng sai luật.
2. **Bỏ sót dẫn chiếu chéo.** Văn bản ghi "theo Điều 6 Thông tư 41" nhưng người tra phải tự tìm tiếp, dễ sót.
3. **Xung đột quy định.** Hai văn bản cùng hiệu lực quy định số liệu khác nhau mà không ai nhận ra.
4. **Không biết mình bị ảnh hưởng khi luật đổi.** Khi SBV ban hành văn bản mới, việc xác định quy trình và văn bản nội bộ nào phải cập nhật hiện làm thủ công, chậm và hay sót — khiến quy định nội bộ âm thầm trở nên trái luật cho tới khi thanh tra phát hiện.

Ba nỗi đau đầu là phần đề bài trực tiếp yêu cầu giải. Nỗi đau thứ tư là phần nhóm chủ động mở rộng (xem Radar Tác động). Hệ quả chung là rủi ro pháp lý và chi phí phạt cao, thời gian rà soát kéo dài, và kiến thức tổ chức không được chuẩn hóa. Theo mô tả đề bài SHB, riêng khâu rà soát này ngốn của các đội tuân thủ khoảng **2–3 giờ mỗi ngày**.

## Giải pháp

Một trợ lý pháp lý dùng chung một bộ não là đồ thị tri thức có chiều thời gian, cung cấp đủ **sáu deliverable mà đề bài yêu cầu**, cộng một lớp sáng tạo mở rộng:

**Sáu deliverable bắt buộc (theo đề):**
- **Chatbot hỏi–đáp có trích nguồn.** Nhân viên hỏi tự nhiên; hệ thống tìm kiếm kết hợp (từ khóa + ngữ nghĩa + lần theo dẫn chiếu), **lọc bỏ điều khoản hết hiệu lực tính đến thời điểm hỏi**, rồi để LLM tổng hợp câu trả lời kèm trích dẫn về đúng Điều/Khoản.
- **Trực quan đồ thị tri thức.** Hiển thị các văn bản và quan hệ (sửa đổi / thay thế / dẫn chiếu) dưới dạng đồ thị tương tác.
- **Dòng thời gian phiên bản điều khoản.** Duyệt chuỗi thay thế để cho thấy một điều khoản đã tiến hóa qua các bản nào.
- **Bộ phát hiện xung đột.** Cảnh báo khi hai điều khoản cùng hiệu lực nhưng quy định số liệu khác nhau.
- **Màn admin cập nhật văn bản.** Nạp văn bản mới vào hệ thống qua giao diện, không cần chạm code.
- **So sánh benchmark với RAG thường.** Đặt cạnh nhau trên cùng dữ liệu để chứng minh điểm khác biệt.

**Lớp sáng tạo mở rộng (điểm cộng "độ mới"), làm sau khi sáu deliverable trên đã chạy:**
- **Radar Tác động.** Khi admin nạp một văn bản sửa đổi, hệ thống tự quét đồ thị và bắn ra báo cáo: văn bản và quy trình nội bộ nào bị ảnh hưởng, ai cần cập nhật. Đây là bước nhảy từ "công cụ tìm kiếm" sang "hệ thống canh gác tuân thủ" — không nằm trong deliverable đề yêu cầu, mà là phần nhóm chủ động thêm để ăn điểm sáng tạo.

Cốt lõi kỹ thuật: mỗi điều khoản được gắn **khoảng hiệu lực [ngày bắt đầu, ngày hết hạn)**, và các quan hệ (sửa đổi, thay thế, dẫn chiếu) được lưu dưới dạng đồ thị. Nhờ vậy hệ thống trả lời đúng theo thời điểm, loại đúng điều khoản bị thay thế một phần, và lần được quan hệ giữa các văn bản. _(Chi tiết kiến trúc, tech stack và kế hoạch demo nằm ở `addendum.md`.)_

## Điểm khác biệt

- **Đồ thị điều khoản có phiên bản theo thời gian — đây mới là tài sản, không phải cái filter.** Cần nói thẳng để không tự đưa cổ vào chỗ bị chặt: bản thân việc *lọc theo ngày* chỉ là một câu truy vấn tầm thường (`effective_date <= asOf < expiry_date`). Độ khó và độ mới nằm ở **thứ mà filter đó đọc lên**: một đồ thị mô hình hóa quan hệ *sửa đổi / thay thế một phần / dẫn chiếu* ở **cấp khoản**, dựng lại được trạng thái luật tại bất kỳ thời điểm nào. RAG thường không có lớp này nên không phân biệt được bản còn và hết hiệu lực; xây được lớp này mới là phần công sức thật. Khi pitch, nhấn vào *mô hình hóa quan hệ*, không nhấn vào *cái WHERE*.
- **Lần theo dẫn chiếu & phát hiện xung đột.** Tự nối điều được dẫn chiếu (graph traversal) và tự đối chiếu hai điều khoản cùng hiệu lực để cảnh báo mâu thuẫn — hai năng lực RAG ngữ nghĩa thuần không làm được, và là phần "AI/logic" rõ nhất của hệ thống.
- **Chủ động thay vì bị động.** Radar Tác động phát hiện rủi ro *trước khi có người hỏi* — điều một chatbot Q&A thuần túy không làm được. Đây là phần nhóm thêm ngoài yêu cầu đề.
- **Tận dụng đúng thế mạnh, không tô vẽ.** Lợi thế không nằm ở việc "tự chế AI" mà ở đồ thị tri thức có chiều thời gian cộng logic lan tỏa tác động — phần khó phải tự thiết kế, LLM thuê ngoài không thay thế được. Đây là lợi thế trung thực và cũng là thứ RAG thường sao chép rất khó.

## Người dùng

**Chính — Nhân viên ngân hàng (cốt lõi):**
- *Cán bộ tuân thủ, pháp chế:* rà soát quy định, chịu rủi ro phạt cao nhất; cần câu trả lời đúng hiệu lực và cảnh báo chủ động khi luật đổi.
- *Cán bộ tín dụng, nghiệp vụ:* tra cứu quy định để xử lý hồ sơ hằng ngày; cần trả lời nhanh, rõ, có nguồn.

**Thứ cấp — Khách hàng (có trong bản demo):** tra cứu các quy định và chính sách công khai liên quan đến sản phẩm, qua cùng giao diện hỏi–đáp nhưng giới hạn ở dữ liệu công khai, không chạm dữ liệu nội bộ. Để tránh biến đây thành lời hứa suông, demo dành **đúng một khoảnh khắc khách hàng cụ thể**: một câu hỏi công khai (ví dụ về một chính sách/quy định công bố) chạy ở chế độ chỉ-dữ-liệu-công-khai, cho thấy cùng bộ não nhưng khác phạm vi truy cập.

Thành công với người dùng: tin tưởng câu trả lời vì có nguồn và đúng hiệu lực, giảm thời gian rà soát, và không còn "trượt" quy định khi luật thay đổi.

## Tiêu chí thành công

Ưu tiên theo hai trọng số nhóm đặt cao nhất: **khả thi kỹ thuật kèm demo chạy thật**, và **độ mới, sáng tạo**. _(Khung chấm điểm chính thức của ban tổ chức sẽ cập nhật sau; các tiêu chí dưới đây là mục tiêu tự đặt, bám sát 6 deliverable của đề.)_

- **Sáu deliverable của đề đều hiện diện và bấm được** — dù ở bản tối thiểu. Một ô bắt buộc để trống mất điểm nặng hơn một tính năng sáng tạo long lanh; vì vậy sáu deliverable phải xong trước khi đánh bóng Radar.
- **Demo chạy thật** trên bộ văn bản mẫu có tình huống sửa đổi và dẫn chiếu, thời gian phản hồi mục tiêu dưới 15 giây mỗi câu (theo API contract sẵn có).
- **Chứng minh điểm khác biệt (benchmark), đa bằng chứng — không đặt hết trứng vào cái bẫy số.** Bẫy giá trị số (RAG thường trả bản cũ, ta trả bản mới + cảnh báo) là màn mạnh *nhưng* dễ bị nghi "tự dựng kịch bản để mình thắng" nếu số là amendment tổng hợp. Vì vậy chuẩn bị **≥2 loại bằng chứng khác biệt, trong đó ít nhất một loại KHÔNG cần giá trị số đổi**: (a) *thay thế một phần* — ta loại đúng khoản đã bị bãi bỏ khỏi câu trả lời, RAG thường vẫn trả; (b) *lần theo dẫn chiếu* — ta tự kéo điều được dẫn chiếu, RAG thường bỏ sót. Cả hai nhìn thấy được mà không phụ thuộc con số. RAG baseline chạy trên **cùng dữ liệu, cùng pipeline**, chỉ khác đúng bước lọc hiệu lực; không làm baseline yếu đi giả tạo. _(Nếu dữ liệu thật có sẵn một giá trị số đổi thì càng tốt — xác minh giờ H0; nếu không, bẫy số là dựng và phải trung thực khi trình bày.)_
- **Bộ phát hiện xung đột hoạt động thật, không phải if-else.** Chuẩn bị **≥2 ca xung đột**, và rule **quét thật trên dữ liệu** (so sánh giá trị số của các khoản cùng chủ đề & cùng hiệu lực) chứ không nhét cứng kết quả — để chịu được cả ca giám khảo chưa thấy trước.
- **Có phương án dự phòng khi demo sập.** LLM API chậm/lỗi giữa lúc pitch là rủi ro thật. Frontend đã có sẵn mock mode; chuẩn bị **bộ câu trả lời cache/canned cho đúng các câu demo chính** để không trắng tay trên sân khấu, và một câu "nếu API lag ta chuyển sang bản đã ghi" trong kịch bản trình bày.
- **Radar hoạt động (điểm cộng):** nạp một văn bản sửa đổi, hệ thống liệt kê đúng các điều khoản và văn bản bị ảnh hưởng.
- **Trích nguồn chính xác:** mọi câu trả lời đều dẫn được về đúng điều, khoản, văn bản nguồn.
- **Giá trị kinh doanh** thể hiện định tính: giảm rủi ro dùng luật sai và rút ngắn thời gian rà soát tuân thủ.

## Phạm vi

Bản demo phải hoàn thành trong **48 giờ thi**, nên phạm vi được siết chặt quanh phần chứng minh được điểm khác biệt. Chia làm ba lớp ưu tiên rõ ràng.

**Bắt buộc — sáu deliverable của đề (ưu tiên tuyệt đối):**
- Nạp một bộ nhỏ văn bản mẫu (khoảng 5–10) có sẵn tình huống *sửa đổi* và *dẫn chiếu*. _(Bộ dữ liệu chưa có sẵn; ứng viên là Thông tư 41 và văn bản sửa đổi — cần chuẩn bị file ngay đầu giờ thi. Đây là critical path, xem `addendum.md`.)_
- Cắt văn bản theo cấu trúc Điều/Khoản/Điểm, tìm kiếm kết hợp, và trích nguồn.
- **Lọc theo hiệu lực (as-of date)** — điểm khác biệt bắt buộc phải có.
- **Chatbot Hỏi–đáp** nối vào frontend qua `POST /api/chat` (đã có sẵn khung React trong repo), phục vụ nhân viên, kèm **một câu hỏi khách hàng** chạy ở chế độ chỉ-dữ-liệu-công-khai.
- **Trực quan đồ thị tri thức** và **dòng thời gian phiên bản điều khoản** render từ dữ liệu quan hệ đã dựng.
- **Bộ phát hiện xung đột** — **≥2 ca**, rule quét thật trên dữ liệu (không nhét cứng).
- **Màn admin/ingest** cập nhật văn bản mới.
- Màn hình so sánh benchmark với RAG thường (đa bằng chứng, xem Tiêu chí thành công), phục vụ pitch.

Sáu deliverable này không cùng độ khó nhưng đều bắt buộc; nếu cháy giờ, mỗi cái có **mức co tối thiểu** thay vì bỏ trống (ví dụ admin = đọc JSON thay cho UI Streamlit, timeline = danh sách thay cho đồ họa). Thứ tự co giãn nằm ở `addendum.md`.

**Ưu tiên sáng tạo — chỉ làm sau khi lớp bắt buộc chạy ổn:**
- **Radar Tác động** phiên bản cơ bản kèm màn hình báo cáo ảnh hưởng (deterministic, một kịch bản).

**Ngoài phạm vi:**
- Không huấn luyện hay tự chế LLM — dùng LLM qua API.
- Không tích hợp toàn bộ kho văn bản thật của SHB; chỉ dùng bộ mẫu.
- Máy Dò Lệch Chuẩn và Văn bản Hợp nhất Sống là hướng mở rộng, chỉ làm nếu còn thời gian.
- Phân quyền và bảo mật cấp doanh nghiệp: chỉ nêu nguyên tắc (API key giữ ở backend), không triển khai đầy đủ.

## Tầm nhìn

Từ một trợ lý tra cứu, sản phẩm hướng tới trở thành **nền tảng trí tuệ tuân thủ (Compliance Intelligence Platform)** cho ngân hàng: liên tục đối chiếu quy định nội bộ với luật hiện hành, tự sinh văn bản hợp nhất luôn cập nhật, cảnh báo tác động khi luật đổi, và lưu vết pháp lý theo thời gian để phục vụ kiểm toán. Mục tiêu dài hạn là biến tuân thủ từ *rà soát thủ công, bị động* thành *giám sát tự động, chủ động* — giảm rủi ro phạt và chuẩn hóa kiến thức pháp lý cho toàn tổ chức.