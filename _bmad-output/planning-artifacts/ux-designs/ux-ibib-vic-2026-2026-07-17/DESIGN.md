---
name: 'Compliance Copilot — Trợ lý tra cứu văn bản ngân hàng'
status: final
created: '2026-07-17'
updated: '2026-07-17'
sources: ['prd.md', 'ARCHITECTURE-SPINE.md', 'brief.md']
colors:
  brand:
    red: '#D81E28'      # SHB red [GIẢ ĐỊNH: hex chính xác cần xác nhận theo brand SHB]
    orange: '#F58220'   # SHB orange/gold accent [GIẢ ĐỊNH]
    redDark: '#B21620'
  base:
    bg: '#F5F7FA'
    surface: '#FFFFFF'
    surfaceAlt: '#F1F5F9'
    border: '#E2E8F0'
    text: '#1F2937'
    textMuted: '#64748B'
  semantic:
    active: '#16A34A'     # còn hiệu lực
    conflict: '#D97706'   # xung đột / cảnh báo (amber)
    superseded: '#94A3B8' # đã thay thế / hết hiệu lực (xám, kèm gạch ngang)
    danger: '#DC2626'     # lỗi hệ thống
    public: '#0EA5E9'     # dữ liệu công khai
    internal: '#7C3AED'   # dữ liệu nội bộ
typography:
  fontUI: '"Be Vietnam Pro", Inter, Arial, sans-serif'   # phủ tiếng Việt tốt [GIẢ ĐỊNH]
  fontMono: '"JetBrains Mono", ui-monospace, monospace'  # clause_id / trích dẫn pháp lý
  scale: { xs: '12px', sm: '14px', base: '16px', lg: '18px', xl: '22px', '2xl': '28px' }
  weight: { regular: 400, medium: 500, semibold: 600, bold: 700 }
rounded: { sm: '6px', md: '8px', lg: '12px', pill: '999px' }
spacing: { base: '4px', scale: [4, 8, 12, 16, 24, 32, 48] }
components: ['Button', 'Input', 'ChatBubble', 'SourceCard', 'StatusBadge', 'ConflictBanner', 'GraphPanel', 'VersionTimeline', 'BenchmarkColumns', 'AsOfPicker', 'ModeToggle', 'AdminUpload']
---

# DESIGN.md — Compliance Copilot

## Brand & Style
Chuyên nghiệp, đáng tin, gợi cảm giác ngân hàng/pháp lý. Tông **SHB đỏ-cam** làm bản sắc và điểm nhấn hành động, trên **nền slate trung tính** để đọc lâu không mỏi và làm dữ liệu (bảng, đồ thị, timeline) nổi rõ. Ưu tiên **rõ ràng hơn hoa mỹ**: đây là công cụ tra cứu tuân thủ, sai một chữ là rủi ro pháp lý.

## Colors
- **Brand:** đỏ `{colors.brand.red}` cho nút chính, logo, tiêu đề nhấn; cam `{colors.brand.orange}` cho điểm nhấn phụ, highlight. Dùng **tiết chế** — chủ yếu accent, không phủ nền lớn.
- **Nền/bề mặt:** `{colors.base.bg}` nền app, `{colors.base.surface}` thẻ/panel, `{colors.base.border}` viền.
- **Ngữ nghĩa (TÁCH khỏi brand — quy tắc lõi):**
  - Còn hiệu lực → `{colors.semantic.active}` (xanh lá)
  - Xung đột / cảnh báo → `{colors.semantic.conflict}` (amber)
  - Đã thay thế / hết hiệu lực → `{colors.semantic.superseded}` (xám) + **gạch ngang chữ**
  - Lỗi hệ thống → `{colors.semantic.danger}`
  - Nguồn công khai → `{colors.semantic.public}`; nội bộ → `{colors.semantic.internal}`
- **Không dùng đỏ brand cho trạng thái "hết hiệu lực"** (tránh lẫn brand với cảnh báo) — hết hiệu lực dùng xám gạch ngang.

## Typography
- **UI:** `{typography.fontUI}` — phủ dấu tiếng Việt. Tiêu đề semibold/bold, thân regular.
- **Mono:** `{typography.fontMono}` cho `clause_id`, số điều/khoản, số văn bản (VD `TT41/Điều 6.3`) — dễ phân biệt, tăng cảm giác "trích dẫn chính xác".
- Thang cỡ chữ theo `{typography.scale}`; thân mặc định `base` (16px), phụ chú `sm`.

## Layout & Spacing
- Lưới desktop-first, nội dung tối đa ~1280px, panel bên có thể mở/thu.
- Khoảng cách theo thang `{spacing.scale}` (bội số 4px). Mật độ **vừa-cao** (nhiều dữ liệu) nhưng chừa thở giữa các khối.

## Elevation & Depth
- Phẳng, viền mảnh `{colors.base.border}` là chính; đổ bóng nhẹ chỉ cho panel nổi (popover, banner, modal).
- 2 mức: `flat` (thẻ thường, chỉ viền), `raised` (bóng `0 2px 8px rgba(15,23,42,.08)` cho lớp nổi).

## Shapes
- Bo góc `{rounded.md}` mặc định; chip/badge dùng `{rounded.pill}`; modal/panel lớn `{rounded.lg}`.

## Components
- **Button:** primary (nền đỏ brand, chữ trắng), secondary (viền + chữ đỏ), ghost (chỉ chữ). Trạng thái hover đậm hơn, disabled xám.
- **Input/Textarea:** viền `border`, focus viền đỏ brand + ring mờ.
- **ChatBubble:** người dùng (nền `surfaceAlt`, phải), hệ thống (nền `surface`, trái) kèm khối nguồn phía dưới.
- **SourceCard:** chip mono `clause_id` + tên văn bản + mô tả; badge trạng thái hiệu lực; bấm được → highlight node đồ thị.
- **StatusBadge:** active/superseded/conflict/public/internal theo màu ngữ nghĩa.
- **ConflictBanner:** dải amber, icon cảnh báo, liệt kê 2 nguồn mâu thuẫn.
- **GraphPanel / VersionTimeline / BenchmarkColumns (2 cột) / AsOfPicker / ModeToggle / AdminUpload:** xem hành vi ở `EXPERIENCE.md`.

## Mockup tham chiếu
- Màn "Trợ lý" (kịch bản KF-1, CAR 8%→9%): [`mockups/mock-troly.html`](mockups/mock-troly.html) — mở bằng trình duyệt. Spine thắng nếu mock lệch.

## Do's and Don'ts
- ✅ Luôn kèm **trích nguồn** cạnh mọi câu trả lời.
- ✅ Phân biệt rõ *còn hiệu lực* vs *đã thay thế* bằng màu + gạch ngang, không chỉ bằng chữ.
- ✅ Cảnh báo xung đột phải **nổi bật nhưng không hoảng loạn** (amber, không đỏ toàn màn).
- ❌ Không dùng đỏ brand cho lỗi/hết hiệu lực (giữ đỏ cho bản sắc + hành động).
- ❌ Không giấu nguồn nội bộ ở chế độ khách hàng (đã chặn ở AD-11) — UI chỉ hiển thị nguồn `public`.
- ❌ Không để màn trắng khi chờ/ lỗi — luôn có trạng thái loading/empty/fallback.
