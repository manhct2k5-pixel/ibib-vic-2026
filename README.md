# Sovereign Compliance AI

Nền tảng trợ lý tuân thủ dành cho ngân hàng, được Team IBIB phát triển trong khuôn khổ Vietnam Innovation Challenge 2026.

Hệ thống hỗ trợ tra cứu quy định theo ngày hiệu lực, đối chiếu nguồn trích dẫn, phát hiện nội dung mâu thuẫn, ngăn sử dụng tài liệu hết hiệu lực và quản trị vòng đời tài liệu. Người dùng có thể sử dụng chatbot trên web hoặc tra cứu trực tiếp khi đang đọc tài liệu bằng browser extension.

## Thành viên Team IBIB

- Bảo
- Mạnh Phan
- Thúy Toàn
- Yến
- Chiến Thắng
- Lan Anh

## Các thành phần chính

| Thành phần | Công nghệ | Vai trò |
|---|---|---|
| Frontend | React 19, TypeScript, Vite | Chatbot, đăng nhập, hồ sơ và giao diện quản trị |
| Backend | FastAPI, Pydantic, SQLModel | API chat, pipeline RAG, ingest và quản lý tài liệu |
| Database | PostgreSQL, pgvector | Lưu tài liệu, điều khoản, quan hệ và vector |
| Browser extension | Next.js, React, Manifest V3 | Tra cứu, tóm tắt và hỏi AI ngay trên Chrome/Edge |
| Knowledge pipeline | BM25, vector search, NetworkX | Truy hồi, mở rộng quan hệ, kiểm tra xung đột và tổng hợp câu trả lời |

## Chức năng

### Chatbot tuân thủ

- Tra cứu quy định bằng ngôn ngữ tự nhiên.
- Trả lời kèm citation và tài liệu nguồn.
- Lọc tài liệu theo ngày hiệu lực.
- Phân biệt phạm vi dành cho nhân viên, khách hàng và quản lý.
- Cảnh báo tài liệu mâu thuẫn hoặc đã được thay thế.
- Lưu lịch sử hội thoại và trạng thái làm việc sau khi reload.
- Đính kèm tài liệu theo phiên và xem văn bản hợp nhất.

### Giao diện quản trị

- Dashboard chất lượng chatbot và hoạt động tuân thủ.
- Quy trình quản lý tài liệu 3 bước:
  1. Chọn thư mục.
  2. Tải tệp lên.
  3. Xác minh thông tin và phê duyệt.
- Quản lý cây thư mục Ngân hàng Nhà nước và tài liệu nội bộ SHB.
- Kiểm tra metadata, ngày hiệu lực và phạm vi áp dụng.
- Xử lý feedback, citation sai và nội dung mâu thuẫn.
- Thiết lập quyền cho nhân viên và quản lý.
- Thông báo khi quản lý cập nhật nội dung mới.

### Browser extension

- Bóng chat nổi trên các trang web và tự đồng bộ khi chuyển tab.
- Bôi chọn văn bản rồi nhấn **Hỏi AI**.
- Đọc tiêu đề, URL và nội dung trang hiện tại.
- Tóm tắt trang bằng AI hoặc chế độ cục bộ dự phòng.
- Đăng nhập qua frontend và đồng bộ vai trò tài khoản.
- Hỗ trợ panel nổi và Side Panel của Chrome/Edge.

Tài liệu chi tiết: [browser-extension/README.md](browser-extension/README.md).

## Cấu trúc repository

```text
.
├── backend/                 # FastAPI, pipeline RAG, ingest và tests
│   ├── api/                 # API routes và database integration
│   ├── db/                  # Schema và Docker Compose PostgreSQL
│   ├── ingest/              # Trích xuất, staging và ingest tài liệu
│   ├── kb/                  # Repository, models và knowledge base
│   ├── pipeline/            # Query, retrieve, expand, conflict, synthesize
│   ├── providers/           # LLM providers
│   └── tests/               # Pytest
├── frontend/                # React + Vite web application
├── browser-extension/       # Chrome/Edge Manifest V3 extension
├── data/                    # Corpus mẫu và dữ liệu tài liệu
├── docs/                    # Kiến trúc, API contract và tài liệu cuộc thi
├── tests/evaluation/        # Bộ đánh giá hệ thống
├── _bmad-output/            # Planning và implementation artifacts
└── docker-compose.yml       # PostgreSQL cục bộ
```

## Yêu cầu môi trường

- Node.js 20 trở lên.
- npm 10 trở lên.
- Python 3.11 trở lên.
- Docker Desktop hoặc Docker Engine nếu dùng PostgreSQL.
- Google Chrome hoặc Microsoft Edge nếu dùng extension.

## Khởi chạy nhanh

### 1. Clone repository

```bash
git clone <repository-url>
cd ibib-vic-2026
```

### 2. Chạy backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn api.main:app --reload --port 8000
```

Trên Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn api.main:app --reload --port 8000
```

Mở tài liệu API tương tác để kiểm tra backend:

```text
http://localhost:8000/docs
```

### 3. Chạy frontend

Mở terminal khác:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend mặc định chạy tại:

```text
http://localhost:5173
```

Để kết nối backend thật, cấu hình `frontend/.env.local`:

```env
VITE_API_MODE=real
VITE_API_BASE_URL=http://localhost:8000
```

Chế độ giao diện mô phỏng không cần backend:

```env
VITE_API_MODE=mock
```

### 4. Build browser extension

```bash
cd browser-extension
npm install
npm run build
```

Sau đó:

1. Mở `chrome://extensions` hoặc `edge://extensions`.
2. Bật **Developer mode**.
3. Chọn **Load unpacked**.
4. Chọn thư mục `browser-extension/out/`.

## Chạy PostgreSQL bằng Docker

Tạo file `.env` ở thư mục gốc và cung cấp ít nhất mật khẩu database:

```env
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_NAME=compliance_db
DB_PORT=5433
```

Khởi động database:

```bash
docker compose up -d db
```

Chuỗi kết nối tương ứng:

```text
postgresql://postgres:your-secure-password@localhost:5433/compliance_db
```

Khai báo chuỗi này trong `backend/.env` bằng biến `DATABASE_URL` nếu muốn backend sử dụng PostgreSQL.

## Biến môi trường

### Backend

Sao chép `backend/.env.example` thành `backend/.env` và cấu hình theo nhu cầu:

```env
LLM_API_KEY=
LLM_BACKUP_API_KEY=
DATABASE_URL=
```

Không đưa API key, mật khẩu hoặc file `.env` thật lên Git.

### Frontend

```env
VITE_API_MODE=mock
VITE_API_BASE_URL=http://localhost:8000
```

Frontend không được chứa khóa LLM hoặc database credential.

## API chính

| Method | Endpoint | Mục đích |
|---|---|---|
| `POST` | `/api/chat` | Gửi câu hỏi đến pipeline tuân thủ |
| `GET` | `/api/graph` | Lấy dữ liệu đồ thị |
| `GET` | `/api/kb/graph` | Đồ thị knowledge base |
| `GET` | `/api/kb/timeline/{clause_id}` | Timeline hiệu lực điều khoản |
| `GET` | `/api/consolidate` | Xem văn bản hợp nhất |
| `POST` | `/api/session/upload` | Tải tài liệu văn bản theo phiên |
| `POST` | `/api/session/upload-pdf` | Tải PDF theo phiên |
| `POST` | `/api/admin/ingest-pdf` | Đưa PDF vào vùng staging |
| `GET` | `/api/admin/staging-documents` | Danh sách tài liệu chờ duyệt |
| `POST` | `/api/admin/approve-document/{doc_code}` | Phê duyệt tài liệu |
| `POST` | `/api/admin/reload` | Nạp lại knowledge base |

API contract chi tiết: [docs/architecture/API_CONTRACT.md](docs/architecture/API_CONTRACT.md).

## Kiểm tra và build

### Backend tests

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

### Frontend

```bash
cd frontend
npm run lint
npm run build
```

### Browser extension

```bash
cd browser-extension
npm run lint
npm run build
```

## Luồng dữ liệu tổng quát

```text
Người dùng
   │
   ├── Web frontend
   └── Browser extension
            │
            ▼
        POST /api/chat
            │
            ▼
Query → Retrieve → Expand → Conflict Check → Synthesize
            │
            ▼
 Repository / PostgreSQL / Corpus mẫu / LLM provider
```

## Tài khoản và phân quyền

Frontend lưu phiên đăng nhập trong `localStorage` bằng khóa:

```text
compliance-ai-session
```

Các vai trò hiện có:

- `employee`: sử dụng chatbot, xem citation và gửi feedback.
- `manager`: sử dụng chatbot và truy cập khu vực quản trị.

Browser extension đọc phiên frontend trên `localhost`, đồng bộ vai trò vào `chrome.storage.local` và chỉ mở chatbot sau khi xác thực thành công.

> Phân quyền phía giao diện chỉ phục vụ trải nghiệm người dùng. Khi triển khai production, backend phải xác thực token và kiểm tra quyền cho mọi API nhạy cảm.

## Bảo mật

- Không commit `.env`, API key, database password hoặc dữ liệu nội bộ.
- Không commit `browser-extension/out.pem`. Đây là khóa riêng dùng để ký extension.
- Không chia sẻ `out.pem` qua chat, email hoặc kho mã nguồn công khai.
- Thu hẹp CORS và `host_permissions` trước khi triển khai production.
- Không tin vai trò do client gửi lên nếu chưa xác thực token ở backend.
- Dữ liệu tài liệu ngân hàng phải được phân loại và kiểm soát quyền truy cập.

## Trạng thái Triển khai (Deployment Status)

Hệ thống đã được cấu hình và triển khai đầy đủ phục vụ cho mục đích chạy thử nghiệm và demo:

### 1. Backend (FastAPI + Docker)
* **Nền tảng:** Render.com (Docker Runtime).
* **Đường dẫn API:** [https://ibib-vic-2026.onrender.com](https://ibib-vic-2026.onrender.com)
* **Trạng thái kiểm tra sức khỏe:** [https://ibib-vic-2026.onrender.com/health](https://ibib-vic-2026.onrender.com/health)
* **Cấu hình:** Sử dụng Dockerfile biên dịch Python 3.12-slim kết hợp cài đặt công cụ nhận diện chữ viết OCR Tesseract tiếng Việt cho tính năng trích xuất PDF/Hình ảnh.

### 2. Database (PostgreSQL + pgvector)
* **Nền tảng:** Neon Serverless PostgreSQL.
* **Cấu hình kết nối:** Đã kết nối tự động với Backend Render qua chuỗi connection string được lưu bảo mật trong Environment Variables của Render dashboard.

### 3. Browser Extension (Chrome/Edge Manifest V3)
* **Bản đóng gói sẵn:** [browser-extension.zip](file:///Users/nguyenquocbao/ibib-vic-2026/browser-extension.zip) (nằm ở thư mục gốc).
* **Cấu hình API mặc định:** Đã được thiết lập trỏ trực tiếp đến Backend Cloud trên Render (`https://ibib-vic-2026.onrender.com`).
* **Hướng dẫn cài đặt chi tiết:** Xem tại [browser-extension/HUONG_DAN_EXTENSION.md](file:///Users/nguyenquocbao/ibib-vic-2026/browser-extension/HUONG_DAN_EXTENSION.md).

## Quy trình làm việc với Git

1. Tạo nhánh cho từng chức năng hoặc lỗi.
2. Không commit file build, khóa bí mật hoặc cấu hình cá nhân.
3. Chạy test và build thành phần đã thay đổi.
4. Tạo commit có nội dung rõ ràng.
5. Mở Pull Request để review trước khi merge vào `main`.

## Tài liệu liên quan

- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)
- [Browser Extension README](browser-extension/README.md)
- [API Contract](docs/architecture/API_CONTRACT.md)
- [Architecture](docs/architecture/)
- [Planning artifacts](_bmad-output/planning-artifacts/)
