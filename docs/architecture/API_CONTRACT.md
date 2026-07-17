# Hợp đồng API mẫu giữa Frontend và Backend

Tài liệu này dùng để thống nhất cách kết nối kỹ thuật trước ngày thi. Nội dung nghiệp vụ và tên trường có thể thay đổi sau khi ban tổ chức công bố đề bài.

## 1. Cấu hình chung

- Phương thức: `POST`
- Endpoint mẫu: `/api/chat`
- Content-Type: `application/json`
- Thời gian chờ phía frontend: `15 giây`
- Địa chỉ backend được cấu hình bằng biến môi trường:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Frontend gọi địa chỉ:

```text
POST {VITE_API_BASE_URL}/api/chat
```

## 2. Request mẫu

```json
{
  "question": "Nội dung yêu cầu của người dùng",
  "asOf": "2026-07-17",
  "mode": "system"
}
```

### Trường bắt buộc

| Trường | Kiểu dữ liệu | Mô tả |
|---|---|---|
| `question` | string | Nội dung người dùng gửi đến hệ thống |

### Trường tùy chọn

| Trường | Kiểu dữ liệu | Mặc định | Mô tả |
|---|---|---|---|
| `asOf` | string (YYYY-MM-DD) | hôm nay | Mốc thời gian lọc hiệu lực |
| `mode` | string | `system` | `system` (đầy đủ) hoặc `baseline` (tắt lọc hiệu lực + dẫn chiếu, phục vụ benchmark) |

## 3. Response thành công

```json
{
  "answer": "Nội dung phản hồi từ hệ thống",
  "sources": [
    {
      "clause_id": "TT41/Điều 6.3",
      "name": "Tên nguồn",
      "description": "Mô tả ngắn về nguồn"
    }
  ],
  "conflictWarning": null,
  "requestId": "request-001",
  "latencyMs": 850
}
```

### Trường dữ liệu

| Trường | Bắt buộc | Kiểu dữ liệu | Mô tả |
|---|---|---|---|
| `answer` | Có | string | Nội dung kết quả chính |
| `sources` | Không | array | Danh sách nguồn tham khảo |
| `requestId` | Không | string | Mã định danh yêu cầu |
| `latencyMs` | Không | number | Thời gian xử lý tính bằng mili giây |

Mỗi phần tử trong `sources` có cấu trúc:

```json
{
  "clause_id": "TT41/Điều 6.3",
  "name": "Tên nguồn",
  "description": "Mô tả nguồn"
}
```

| Trường | Bắt buộc | Kiểu | Mô tả |
|---|---|---|---|
| `clause_id` | Có | string | Định danh Điều/Khoản để frontend click-through về nguồn gốc |
| `name` | Có | string | Tên nguồn |
| `description` | Không | string | Mô tả ngắn |

## 4. Response khi có lỗi

Backend nên trả về mã HTTP phù hợp và một trong hai trường `detail` hoặc `message`.

```json
{
  "detail": "Nội dung lỗi"
}
```

Hoặc:

```json
{
  "message": "Nội dung lỗi"
}
```

Ví dụ mã trạng thái:

| Mã HTTP | Ý nghĩa |
|---|---|
| `400` | Request không hợp lệ |
| `422` | Dữ liệu đầu vào không hợp lệ |
| `500` | Backend xử lý thất bại |
| `503` | Dịch vụ tạm thời không khả dụng |

## 5. Quy ước tích hợp

- Frontend không chứa API key.
- API key và thông tin bí mật chỉ được lưu ở backend.
- Backend phải cho phép CORS đối với địa chỉ chạy frontend.
- Backend phải luôn trả về JSON.
- Trường `answer` phải là chuỗi khi request thành công.
- Khi chưa có backend thật, frontend sử dụng chế độ `mock`.
- Khi tích hợp backend, chuyển `VITE_API_MODE` thành `real`.

## 6. Nội dung cần thống nhất trong ngày thi

Sau khi có đề chính thức, frontend và backend cần thống nhất lại:

- Endpoint chính thức.
- Tên và cấu trúc request.
- Tên và cấu trúc response.
- Cách truyền tệp hoặc dữ liệu bổ sung.
- Quy tắc hiển thị nguồn.
- Quy tắc báo lỗi.
- Thời gian chờ và phương án dự phòng.