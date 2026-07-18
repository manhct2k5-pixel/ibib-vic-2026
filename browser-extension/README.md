# SovAI — Browser Extension

Tiện ích trợ lý tuân thủ dành cho Google Chrome và Microsoft Edge, xây dựng bằng Next.js, React, TypeScript và Chrome Extension Manifest V3.

Extension hoạt động độc lập trong thư mục `browser-extension/`, không dùng chung quá trình build với `frontend/`. Giao diện chính được xuất tĩnh và đóng gói vào thư mục `out/`.

## Chức năng chính

- Bóng chat AI nổi trên các trang web và tự đồng bộ khi chuyển tab.
- Panel trợ lý mở trực tiếp trên trang hoặc trong Side Panel của trình duyệt.
- Bôi chọn văn bản và nhấn **Hỏi AI** để đưa nội dung vào cuộc trò chuyện.
- Menu chuột phải để hỏi AI về đoạn văn đang chọn.
- Nhận diện tiêu đề, URL và favicon của trang hiện tại.
- Đọc và tóm tắt nội dung trang đang xem.
- Tóm tắt cục bộ dự phòng khi backend không kết nối được.
- Đính kèm các tệp văn bản `.txt`, `.md`, `.csv` và `.json`.
- Lưu lịch sử câu hỏi trong `chrome.storage.local`.
- Bắt buộc đăng nhập trước khi sử dụng và đồng bộ vai trò tài khoản.
- Tự quay về tab đang làm việc sau khi đăng nhập thành công.

## Yêu cầu môi trường

- Node.js 20 trở lên.
- npm 10 trở lên.
- Google Chrome hoặc Microsoft Edge hỗ trợ Manifest V3 và Side Panel.
- Frontend chạy tại `http://localhost:5173`.
- Backend mặc định chạy tại `http://localhost:8000`.

## Cài đặt dependencies

Từ thư mục dự án:

```bash
cd browser-extension
npm install
```

## Build extension

```bash
npm run build
```

Lệnh build thực hiện hai bước:

1. Next.js tạo static export.
2. `scripts/prepare-extension.mjs` chuẩn bị các tệp Manifest V3 và đưa kết quả vào `browser-extension/out/`.

Sau khi hoàn tất, terminal sẽ hiển thị:

```text
Extension package ready in browser-extension/out
```

## Cài đặt trên Chrome

1. Truy cập `chrome://extensions`.
2. Bật **Developer mode**.
3. Chọn **Load unpacked**.
4. Chọn thư mục `browser-extension/out/`.
5. Ghim biểu tượng **SovAI** lên thanh công cụ nếu cần.

Sau mỗi lần sửa mã nguồn:

1. Chạy lại `npm run build`.
2. Mở `chrome://extensions`.
3. Nhấn **Reload** trên extension.
4. Tải lại trang web đang kiểm tra để content script mới được kích hoạt.

## Cài đặt trên Microsoft Edge

1. Truy cập `edge://extensions`.
2. Bật **Developer mode**.
3. Chọn **Load unpacked**.
4. Chọn thư mục `browser-extension/out/`.

## Đăng nhập và phân quyền

Khi chưa đăng nhập, extension chỉ hiển thị màn hình yêu cầu truy cập trang chủ.

1. Nhấn **Truy cập trang chủ**.
2. Extension mở `http://localhost:5173/login` trong tab mới.
3. Đăng nhập bằng tài khoản nhân viên hoặc quản lý.
4. Frontend lưu phiên trong `localStorage` với khóa `compliance-ai-session`.
5. Content script đồng bộ trạng thái và vai trò vào `chrome.storage.local`.
6. Extension tự mở khóa và chuyển về tab người dùng đang làm việc.

Vai trò được hỗ trợ:

- `employee`: nhân viên.
- `manager`: quản lý.

Nhấn vào logo **SovAI** trong extension sẽ mở trang chatbot tại `http://localhost:5173/chatbot`.

## Bật bóng chat

1. Nhấn biểu tượng extension trên thanh công cụ.
2. Bật công tắc **Bóng chat trên trang**.
3. Bóng AI xuất hiện ở góc phải dưới của các trang `http://` và `https://`.
4. Nhấn bóng AI để mở hoặc đóng panel trợ lý.

Bóng chat không thể xuất hiện trên các trang đặc quyền như:

- `chrome://extensions`.
- `edge://extensions`.
- Chrome Web Store.
- Trang tab mới và các trang hệ thống của trình duyệt.

## Hỏi AI từ đoạn văn được chọn

1. Bôi chọn nội dung trên trang web.
2. Nhấn nút **Hỏi AI** xuất hiện cạnh đoạn chọn.
3. Nội dung được đưa thẳng vào ô chat.

Cũng có thể nhấp chuột phải vào đoạn đã chọn và dùng mục **Hỏi SovAI**.

Extension chỉ sử dụng một giao diện tại một thời điểm:

- Nếu panel nổi đang mở, nội dung được gửi vào panel nổi.
- Nếu Side Panel Chrome đang mở, nội dung được gửi vào Side Panel.
- Nếu chưa mở giao diện nào và bóng chat đang bật, panel nổi được ưu tiên.

## Tóm tắt trang hiện tại

Thanh ngữ cảnh phía trên ô chat hiển thị trang đang xem. Nhấn **Tóm tắt** để:

1. Đọc phần văn bản chính của trang.
2. Loại bỏ script, style, menu, footer, form và nội dung ẩn.
3. Giới hạn dữ liệu đầu vào để tránh request quá lớn.
4. Gửi nội dung đến `POST /api/chat` để tóm tắt bằng AI.

Nếu backend trả lỗi kết nối, extension tự tạo bản tóm tắt cục bộ thay vì hiển thị lỗi đỏ.

## API chatbot

Endpoint mặc định:

```text
POST http://localhost:8000/api/chat
```

Request mẫu:

```json
{
  "question": "Nội dung câu hỏi",
  "audience": "employee",
  "mode": "system"
}
```

Backend cần cho phép request từ extension. Nếu xuất hiện `Failed to fetch`, hãy kiểm tra:

- Backend có đang chạy tại cổng `8000` không.
- CORS có cho phép origin `chrome-extension://...` hoặc `edge-extension://...` không.
- URL API có đúng không.
- Firewall hoặc proxy nội bộ có chặn request không.

## Các lệnh phát triển

```bash
# Chạy Next.js ở chế độ phát triển
npm run dev

# Kiểm tra ESLint
npm run lint

# Build static extension
npm run build
```

## Cấu trúc thư mục

```text
browser-extension/
├── app/
│   ├── popup/             # Popup bật/tắt bóng chat
│   ├── sidepanel/         # Giao diện chatbot
│   ├── composer.css       # Giao diện thanh chat và panel
│   └── globals.css        # Style nền tảng
├── public/
│   ├── manifest.json      # Manifest V3
│   ├── background.js      # Service worker, tab và context menu
│   ├── content.js         # Bóng chat, đọc trang, đồng bộ đăng nhập
│   └── content.css        # Style được chèn vào website
├── scripts/
│   └── prepare-extension.mjs
├── out/                   # Kết quả build, không commit
├── package.json
└── README.md
```

## Đóng gói CRX và khóa PEM

Chrome có thể tạo hai tệp khi chọn **Pack extension**:

- `out.crx`: gói extension đã ký.
- `out.pem`: khóa riêng dùng để ký và cập nhật extension.

> **Cảnh báo bảo mật:** Không commit, gửi qua chat, email hoặc chia sẻ công khai tệp `out.pem`. Người có khóa này có thể ký bản cập nhật với danh tính extension của bạn.

Hãy lưu `out.pem` trong kho bí mật hoặc trình quản lý mật khẩu của tổ chức. Khi đóng gói phiên bản mới, sử dụng lại đúng khóa PEM để giữ nguyên extension ID.

## Lưu ý triển khai production

- Thay URL `localhost` bằng domain frontend và backend thật.
- Thu hẹp `host_permissions` thay vì giữ `<all_urls>` nếu không cần thiết.
- Chỉ cho phép các định dạng tệp và kích thước cần thiết.
- Không lưu token nhạy cảm dưới dạng văn bản thuần trong `chrome.storage.local`.
- Xác thực và phân quyền lại ở backend; không chỉ tin vào vai trò do client gửi lên.
- Kiểm tra chính sách CORS, CSP và quyền Manifest trước khi phát hành.
