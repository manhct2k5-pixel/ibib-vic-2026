# Giải pháp công nghệ — Compliance Copilot (ibib-vic-2026)

> Trợ lý tra cứu & hợp nhất văn bản pháp lý ngân hàng. Cập nhật: 2026-07-18.

---

## 1. Bài toán & giải pháp

**Bài toán:** Nhân viên ngân hàng phải đọc hàng nghìn văn bản pháp lý rời rạc (Luật,
Nghị định, Thông tư NHNN, quy chế nội bộ), liên tục bị sửa đổi/thay thế. Việc xác
định "điều khoản nào còn hiệu lực tại thời điểm X", "văn bản nào sửa văn bản nào",
"đọc theo thứ tự ra sao" rất tốn công và dễ sai.

**Giải pháp:** Một trợ lý AI hỏi–đáp có trích nguồn, đúng-thời-điểm (as-of), tự phát
hiện xung đột, và đặc biệt: **tự dựng "văn bản hợp nhất"** từ tài liệu người dùng
đính kèm — gộp văn bản gốc + các sửa đổi thành một bản đọc liền mạch, kèm bản đồ quan
hệ và hướng dẫn đọc.

Hệ thống gồm **2 luồng dữ liệu song song**:
- **Luồng DB (corpus doanh nghiệp):** hỏi–đáp trên kho văn bản đã được duyệt/seed
  trong PostgreSQL (RAG + đồ thị quan hệ + lọc hiệu lực).
- **Luồng phiên (tài liệu upload):** phân tích & hợp nhất **chỉ từ file người dùng
  tải lên**, in-memory, ephemeral — không đụng DB (tích hợp DB là bước phát triển sau).

---

## 2. Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend — React 19 + TypeScript + Vite 8                   │
│  Chat UI · Bản đồ quan hệ (force-graph) · Văn bản hợp nhất   │
│  Upload PDF · Cá nhân hoá (localStorage) · Phân quyền vai trò│
└───────────────┬─────────────────────────────────────────────┘
                │ REST/JSON (fetch)
┌───────────────▼─────────────────────────────────────────────┐
│  Backend — FastAPI (Python 3.12)                            │
│  ┌─────────────────────┐   ┌──────────────────────────────┐ │
│  │ Luồng DB (RAG)      │   │ Luồng phiên (upload)         │ │
│  │ KnowledgeBase       │   │ session_store (in-memory)    │ │
│  │ run_pipeline        │   │ doc_analyze · session_analyze│ │
│  │ (retrieve→expand→   │   │ pdf_ingest (+OCR)            │ │
│  │  temporal→conflict→ │   │ build_session_consolidated   │ │
│  │  synthesize)        │   │                              │ │
│  └──────────┬──────────┘   └──────────────────────────────┘ │
│             │ providers/llm (OpenAI-compat) ─────────────────┼──► LLM (FPT DeepSeek)
└─────────────┼───────────────────────────────────────────────┘
              │ SQLModel / psycopg2
┌─────────────▼───────────────────────────────────────────────┐
│  PostgreSQL 18 (Neon, pgvector)                             │
│  dwh: van_ban, dieu_khoan, qh_dkhoan, anh_xa(vector)        │
│  staging: van_ban_ngoai, quy_che_noi_bo, etl_log            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Stack công nghệ

### Backend
| Thành phần | Công nghệ | Vai trò |
|---|---|---|
| Web framework | **FastAPI** + Uvicorn | REST API, async |
| Ngôn ngữ | **Python 3.12** | |
| ORM/DB | **SQLModel** + SQLAlchemy + **psycopg2** | Ánh xạ bảng dwh/staging |
| Cơ sở dữ liệu | **PostgreSQL 18 (Neon cloud)** + **pgvector** | Corpus + vector embedding |
| Tìm kiếm | **rank-bm25** (BM25Okapi) | Retrieve văn bản theo từ khóa tiếng Việt |
| Đồ thị | **networkx** (DiGraph) | Quan hệ AMENDS/SUPERSEDES/REFERENCES/GUIDES |
| LLM | **httpx** → OpenAI-compat (**FPT DeepSeek-V4**) | Trích quan hệ, tổng hợp; MockLLM fallback |
| Bóc tách PDF | **pypdf**, **pdfplumber** | Đọc lớp text PDF số |
| OCR | **pytesseract** (tesseract `vie`) + **pypdfium2** | PDF scan/font hỏng (render + OCR song song) |
| Bóc tách DOCX | **python-docx** | |

### Frontend
| Thành phần | Công nghệ |
|---|---|
| Framework | **React 19** + **TypeScript** |
| Build | **Vite 8** |
| Trực quan đồ thị | **react-force-graph-2d** |
| Lint | oxlint |
| Lưu client | localStorage (lịch sử, bookmark, phiên đăng nhập) |

### AI/LLM
- Provider theo interface `LLMProvider.generate(system, prompt, timeout)`.
- Chọn provider theo env: OpenAI-compat (FPT DeepSeek) hoặc Anthropic; **MockLLM**
  (deterministic, offline) khi thiếu key hoặc để test/đường lui.
- Cấu hình qua `backend/.env`: `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`,
  `DATABASE_URL`.

---

## 4. Các luồng xử lý chính

### 4.1 Hỏi–đáp trên corpus DB (`POST /api/chat`)
Pipeline tuyến tính (pipes-and-filters):
1. **Retrieve** — BM25 trên corpus, lọc theo vai trò/phòng ban (fail-closed).
2. **Expand** — mở rộng theo cạnh REFERENCES/GUIDES trong đồ thị.
3. **Overlay phiên (AD-13)** — trộn tài liệu đính kèm phiên (nếu có `sessionId`).
4. **Temporal filter** — `is_active(clause, asOf)`: `eff ≤ asOf < exp`.
5. **Conflict check** — cảnh báo khi 2 quy định cùng hiệu lực mâu thuẫn số liệu.
6. **Synthesize** — câu trả lời ngắn gọn (markdown) + danh sách nguồn + cảnh báo.

Trả về: `{answer, sources[], conflictWarning, requestId, latencyMs}`.

### 4.2 Văn bản hợp nhất từ tài liệu upload (session-only)
Xem chi tiết `docs/architecture/SESSION_CONSOLIDATION.md`. Tóm tắt:
1. **Upload nhanh** (`POST /api/session/upload-pdf`): đọc PDF (OCR nếu font hỏng/scan),
   cắt theo Điều, metadata bằng regex (mã văn bản ưu tiên từ tên file). Chưa gọi LLM.
2. **Phân tích khi gửi** (`POST /api/session/analyze`): LLM trích quan hệ liên-văn-bản
   (AMENDS/SUPERSEDES/REFERENCES/CONSOLIDATES) + metadata → dựng **bản đồ quan hệ**,
   **thứ tự đọc**, **hướng dẫn đọc**.
3. **Hợp nhất** (`GET /api/session/consolidated`): chọn **1 văn bản nền** (VBHN → văn
   bản bị sửa đổi → văn bản lớn nhất), gộp sửa đổi từ các file khác, đánh dấu từng Điều
   bị sửa (amendedBy). Chỉ **một** văn bản hợp nhất tổng hợp.
4. **Xoá tài liệu** (`DELETE /api/session/doc`): gỡ file khỏi phiên, cập nhật lại đồ thị.

---

## 5. Tính năng nổi bật
- **Đúng-thời-điểm (as-of):** tra cứu quy định còn hiệu lực tại một ngày bất kỳ.
- **Trích nguồn:** mỗi câu trả lời gắn `clause_id`, trạng thái hiệu lực, văn bản thay thế.
- **Phát hiện xung đột:** cảnh báo khi quy định NHNN và nội bộ SHB lệch số liệu.
- **Văn bản hợp nhất từ file upload:** gộp gốc + sửa đổi, có bản đồ quan hệ + hướng dẫn đọc.
- **OCR tiếng Việt:** đọc được cả PDF scan/font hỏng (render trang + tesseract, chạy song song).
- **Chat-first (FR-19):** mọi output (đồ thị, hợp nhất) render inline ngay trong chat.
- **Cá nhân hoá:** lịch sử tra cứu, bookmark, vai trò (Quản lý/Nhân viên) — lưu localStorage.

---

## 6. Bảo mật & phân quyền
- **Fail-closed theo vai trò/phạm vi:** chỉ đúng vai trò nhân viên/nội bộ mới thấy
  văn bản `internal`; khách hàng chỉ thấy `public`.
- **Phân quyền theo phòng ban:** nhân viên chỉ thấy nội bộ phòng mình (trừ Pháp chế).
- **Key LLM chỉ ở backend** (`backend/.env`, không log, không gửi ra frontend).
- **Tài liệu phiên không persist:** upload chỉ nằm in-memory theo `sessionId`, mất khi
  hết phiên — không rò sang phiên khác, không đổ vào kho chung.

---

## 7. Hạn chế hiện tại & hướng phát triển
- **Human-in-the-loop cho hợp nhất (Bước 4):** bản AI sinh ra là **nháp hỗ trợ Pháp
  chế**, cần dashboard duyệt + diff trực quan — CHƯA làm (patch admin/DB sau).
- **Trace-back footnote** đầy đủ (số/ngày văn bản nguồn cho từng điều) — cần bổ sung.
- **Tách xuống mức Khoản/Chương** (hiện mới mức Điều).
- **Hợp nhất tài liệu upload với corpus DB** khi văn bản đích chưa được tải lên.
- **OCR:** phụ thuộc tesseract + gói `vie`; PDF scan chất lượng thấp có thể sai chữ.

---

## 8. Vận hành

```bash
# Backend (cần backend/.env: LLM_API_KEY, DATABASE_URL)
cd ibib-vic-2026
./backend/.venv/bin/python -m uvicorn backend.api.main:app --reload --port 8000

# Frontend (frontend/.env.local: VITE_API_MODE=real, VITE_API_BASE_URL)
cd frontend && npm run dev
```
Yêu cầu hệ thống cho OCR: `brew install tesseract` + gói tiếng Việt `vie.traineddata`
(tessdata_fast) trong thư mục tessdata của tesseract.
