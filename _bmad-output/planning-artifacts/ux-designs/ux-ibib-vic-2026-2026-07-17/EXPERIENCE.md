---
name: 'Compliance Copilot — Experience'
status: final
created: '2026-07-17'
updated: '2026-07-17'
sources: ['prd.md', 'ARCHITECTURE-SPINE.md', 'DESIGN.md']
---

# EXPERIENCE.md — Compliance Copilot

> Cách sản phẩm *hoạt động*. Bản sắc thị giác nằm ở `DESIGN.md`; tài liệu này tham chiếu token bằng cú pháp `{colors.semantic.active}`. Khi xung đột, spine thắng mọi mock.

## Foundation
- **Form-factor:** web, **desktop-first** (màn ≥1280px là chính; xuống 1024 vẫn dùng được). Không tối ưu mobile trong MVP.
- **Nền tảng:** React + TypeScript + Vite (repo sẵn có). Không dùng design-system ngoài; tự dựng component nhẹ theo `DESIGN.md`.
- **Ngôn ngữ:** toàn bộ tiếng Việt.

## Information Architecture
Một app, 3 khu vực chính + 1 màn admin tách riêng:

- **Trợ lý (mặc định)** — bố cục 2 cột:
  - *Cột chính:* hội thoại Hỏi–đáp (chat) + khối trích nguồn dưới mỗi câu trả lời.
  - *Cột phụ (thu/mở được):* tab **Đồ thị tri thức** và tab **Dòng thời gian** của điều khoản đang xem.
  - *Thanh trên:* logo/tên, **AsOfPicker** (chọn mốc thời gian), **ModeToggle** (Nhân viên / Khách hàng).
- **Benchmark** — màn riêng, 2 cột side-by-side: *RAG thường* vs *Compliance Copilot* cho cùng câu hỏi.
- **Admin / Nạp văn bản** — màn riêng (có thể là Streamlit tách): upload/nhập corpus, xem trạng thái, kích hoạt Radar.

*Đóng IA:* mọi nhu cầu trong PRD đều có bề mặt — hỏi (chat), thấy quan hệ (đồ thị), thấy lịch sử (timeline), thấy khác biệt (benchmark), quản trị (admin). Radar hiển thị trong màn Admin dưới dạng báo cáo tác động.

## Voice and Tone (microcopy)
- **Giọng:** chuyên nghiệp, điềm tĩnh, chính xác. Không đùa, không cường điệu.
- **Nguyên tắc:** nói rõ *nguồn* và *thời điểm*. Ví dụ trả lời luôn có mệnh đề "theo … còn hiệu lực đến …".
- Placeholder ô hỏi: *"Nhập câu hỏi về quy định, ví dụ: Tỷ lệ an toàn vốn tối thiểu hiện nay?"*
- Cảnh báo thay thế: *"⚠ Điều khoản cũ đã bị thay thế — đang dùng bản mới nhất."*
- Cảnh báo xung đột: *"⚠ Phát hiện quy định có thể xung đột giữa 2 nguồn dưới đây."*
- Lỗi API: *"Hệ thống đang bận. Đã chuyển sang bản trả lời đã lưu."* (fallback AD-9).

## Component Patterns (hành vi — visual ở DESIGN.md)
- **SourceCard:** hiện `clause_id` (mono), tên văn bản, badge trạng thái. Bấm → cuộn/nhấp nháy node tương ứng trong Đồ thị + mở Timeline của điều đó.
- **StatusBadge:** ánh xạ trạng thái điều khoản → màu ngữ nghĩa. "Đã thay thế" luôn kèm **gạch ngang** phần văn bản trích.
- **ConflictBanner:** hiện phía trên câu trả lời khi `conflictWarning` khác null; liệt kê 2 nguồn + nút "xem chi tiết".
- **GraphPanel:** đồ thị lực (react-force-graph-2d) từ JSON `{nodes,edges}`; node = văn bản/điều khoản, cạnh màu theo loại (sửa đổi/thay thế/dẫn chiếu). Bấm node → chi tiết + timeline.
- **VersionTimeline:** trục ngang các phiên bản một điều khoản theo `SUPERSEDED_BY`, mốc có ngày hiệu lực; bản hiện hành nổi bật, bản cũ mờ + gạch ngang.
- **BenchmarkColumns:** 2 cột đồng bộ cuộn; đánh dấu chỗ khác biệt (bản cũ vs mới, thiếu dẫn chiếu).
- **AsOfPicker:** chọn ngày; đổi → truy vấn lại với `asOf` (AD-6). Mặc định "Hôm nay".
- **ModeToggle:** Nhân viên ↔ Khách hàng; ở Khách hàng chỉ hiện nguồn `public` (AD-11), có nhãn rõ "Chế độ công khai".
- **AdminUpload:** kéo-thả/nhập văn bản → tiến trình → thông báo "đã nạp, đồ thị cập nhật"; nút "Chạy Radar".

## State Patterns
Mỗi bề mặt dữ liệu có 4 trạng thái: **loading · empty · error · success**.
- *Chat loading:* bong bóng "đang tra cứu…" + skeleton nguồn.
- *Empty:* chưa hỏi gì → gợi ý 3 câu mẫu (bao gồm 1 câu "bẫy thời gian" và 1 câu khách hàng).
- *Error/timeout:* chuyển fallback canned (AD-9), báo rõ đang dùng bản đã lưu.
- *Graph/Timeline empty:* "Chọn một nguồn để xem quan hệ / lịch sử phiên bản."

## Interaction Primitives
- Enter gửi câu hỏi; Shift+Enter xuống dòng.
- Bấm SourceCard ↔ highlight node (hai chiều: bấm node cũng highlight nguồn).
- AsOfPicker và ModeToggle đổi → truy vấn lại, giữ lại câu hỏi cuối.
- Timeout FE 15s (theo API contract) → fallback.

## Accessibility Floor (hành vi — tương phản màu ở DESIGN.md)
- Tương phản chữ/nền ≥ WCAG AA. Trạng thái **không chỉ bằng màu**: kèm icon + chữ (VD "Đã thay thế" + gạch ngang, không chỉ màu xám).
- Điều hướng bàn phím đầy đủ; focus ring rõ (đỏ brand).
- Nút/nguồn có nhãn ARIA; đồ thị có bảng thay thế (danh sách quan hệ) cho người dùng không thao tác đồ hình.

## Trạng thái hiệu lực & cảnh báo *(mục riêng cho sản phẩm này)*
Quy ước hiển thị nhất quán mọi nơi (chat, source, graph, timeline):
| Trạng thái | Màu | Ký hiệu bổ sung |
|---|---|---|
| Còn hiệu lực | `{colors.semantic.active}` | badge "Hiệu lực" |
| Đã thay thế / hết hiệu lực | `{colors.semantic.superseded}` | **gạch ngang** + badge "Đã thay thế" |
| Xung đột | `{colors.semantic.conflict}` | banner + icon ⚠ |

## Chế độ công khai vs nội bộ *(mục riêng)*
- ModeToggle rõ ràng; ở **Khách hàng**, thanh trên đổi nhãn "Chế độ công khai" (màu `{colors.semantic.public}`), và UI đảm bảo mọi nguồn đều `public` (khớp AD-11).
- Chuyển chế độ không mất lịch sử chat, nhưng đánh dấu rõ câu nào trả ở chế độ nào.

## Key Flows (nhân vật có tên — theo UJ của PRD)
- **KF-1 — Hà kiểm tra ngưỡng đang hiệu lực (UJ-1).** Hà gõ "Tỷ lệ an toàn vốn tối thiểu hiện nay?" → thấy skeleton → **climax:** câu trả lời "9% theo TT22/Điều 1, hiệu lực từ 2020-01-01", kèm SourceCard mono + banner "điều khoản cũ (8%) đã bị thay thế". Hà bấm nguồn → node sáng + timeline 8%→9%.
- **KF-2 — Nam gặp điều khoản bị thay thế một phần (UJ-2).** Nam hỏi về quy trình có 1 khoản bị bãi bỏ → **climax:** câu trả lời chỉ dùng phần còn hiệu lực, khoản bị bãi bỏ hiện xám gạch ngang với ghi chú "đã hết hiệu lực".
- **KF-3 — Linh (khách hàng) hỏi chính sách công khai (UJ-3).** Linh chuyển ModeToggle sang Khách hàng → nhãn "Chế độ công khai" → hỏi → **climax:** trả lời chỉ từ nguồn `public`, không lộ nội bộ.
- **KF-4 — Tú (admin) nạp văn bản mới → Radar (UJ-4, stretch).** Tú kéo-thả văn bản sửa đổi vào AdminUpload → "đã nạp, đồ thị cập nhật" → bấm "Chạy Radar" → **climax:** báo cáo tác động liệt kê điều khoản/văn bản bị ảnh hưởng.
- **KF-5 — Trình bày benchmark (phục vụ pitch).** Mở màn Benchmark → nhập câu bẫy → **climax:** 2 cột: RAG thường trả 8% (sai), Copilot trả 9% + cảnh báo (đúng), chỗ khác biệt được tô.
