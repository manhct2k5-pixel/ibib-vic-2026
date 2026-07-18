# Team SovAI – Frontend Starter

Bộ khung frontend dùng chung cho Team SovAI, xây dựng bằng React, TypeScript và Vite.

Tên sản phẩm, màu sắc, logo và luồng nghiệp vụ sẽ được điều chỉnh sau khi ban tổ chức công bố đề thi.

## Yêu cầu

- Node.js
- npm

Kiểm tra phiên bản:

```powershell
node --version
npm --version
```

## Cài đặt

Từ thư mục gốc của repository:

```powershell
cd frontend
npm install
```

## Cấu hình môi trường

Tạo file `.env.local` từ file mẫu:

```powershell
Copy-Item .env.example .env.local
```

Cấu hình mặc định:

```env
VITE_API_MODE=mock
VITE_API_BASE_URL=http://localhost:8000
```

Quy ước:

- `mock`: dùng phản hồi mô phỏng, không cần backend.
- `real`: gọi backend thật tại địa chỉ `VITE_API_BASE_URL`.
- Không commit file `.env.local`.
- Không lưu API key trong frontend.

## Chạy frontend

```powershell
npm run dev
```

Mở địa chỉ được Vite hiển thị, thường là:

```text
http://localhost:5173
```

## Kiểm tra bản build

```powershell
npm run build
```

Bản build được tạo trong thư mục `dist`.

Thư mục `dist` không được commit lên GitHub.

## Kiểm tra mã nguồn

```powershell
npm run lint
```

## Kết nối backend

Frontend hiện gọi API:

```text
POST /api/chat
```

Request mẫu:

```json
{
  "question": "Nội dung yêu cầu của người dùng"
}
```

Response tối thiểu:

```json
{
  "answer": "Nội dung phản hồi",
  "sources": []
}
```

Chi tiết được mô tả tại:

```text
docs/architecture/API_CONTRACT.md
```

## Checklist ngày thi

Sau khi nhận đề chính thức, cần cập nhật:

- Tên sản phẩm.
- Logo và màu sắc.
- Nội dung giới thiệu.
- Các trường nhập liệu.
- Cấu trúc request và response.
- Địa chỉ backend.
- Cách hiển thị kết quả và nguồn.
- Ba luồng demo chính.
- Thông báo lỗi và phương án dự phòng.

## Quy tắc làm việc

- Không sửa trực tiếp trên `main`.
- Tạo nhánh riêng cho từng nhiệm vụ.
- Không đưa API key hoặc dữ liệu riêng lên GitHub.
- Chạy `npm run build` trước khi commit.
- Tạo Pull Request để kiểm tra trước khi merge.
