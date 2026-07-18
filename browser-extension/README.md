# Sovereign Compliance AI — Browser Extension

Extension Manifest V3 độc lập cho Chrome và Microsoft Edge. Thư mục này không phụ thuộc vào build của `frontend/` và không sửa `backend/`.

## Cài đặt Chrome

1. Mở `chrome://extensions`.
2. Bật **Developer mode**.
3. Trong `browser-extension/`, chạy `npm install` rồi `npm run build`.
4. Chọn **Load unpacked**.
5. Chọn thư mục `browser-extension/out/`.
6. Bấm biểu tượng extension và chọn **Mở Side Panel**.

## Cài đặt Edge

1. Mở `edge://extensions`.
2. Bật **Developer mode**.
3. Chạy `npm install` và `npm run build`.
4. Chọn **Load unpacked** và trỏ đến `browser-extension/out/`.

## Sử dụng

- Backend mặc định: `http://localhost:8000`.
- Có thể đổi API URL và vai trò trong nút cài đặt của Side Panel.
- Bôi chọn văn bản trên trang rồi bấm **Đoạn chọn**, hoặc nhấp chuột phải và chọn **Tra cứu với Sovereign Compliance AI**.
- Extension gửi request `POST /api/chat` theo contract hiện có.

## Phát triển

- Giao diện dùng Next.js App Router, React và TypeScript trong `app/`.
- `npm run dev`: chạy giao diện ở chế độ phát triển.
- `npm run build`: static export và đóng gói Manifest V3 vào `out/`.
- Script `scripts/prepare-extension.mjs` tách inline hydration script của Next.js thành file cục bộ để tuân thủ Content Security Policy của Manifest V3.

## Lưu ý triển khai

`host_permissions` hiện dùng `<all_urls>` để hỗ trợ API nội bộ có hostname khác nhau. Khi đóng gói phát hành chính thức, nên thay bằng domain API cụ thể của tổ chức.
