# Hướng dẫn sử dụng Tiện ích mở rộng (Browser Extension)

**Sovereign Compliance AI Extension** là tiện ích mở rộng chạy độc lập trên Google Chrome và Microsoft Edge (chuẩn Manifest V3). Tiện ích giúp bạn tra cứu nhanh quy định pháp lý, kiểm tra tính tuân thủ hoặc tóm tắt tài liệu ngay khi đang đọc thông tin trên trình duyệt.

---

## 🚀 Các tính năng chính

- **Tra cứu nhanh từ văn bản bôi đen:** Bôi đen đoạn văn bản bất kỳ trên trang web → Click chuột phải → Chọn **Tra cứu với Sovereign Compliance AI**.
- **Tóm tắt trang web:** Tự động đọc và tóm tắt nhanh nội dung của tab hiện tại (chỉ ra các nghĩa vụ, mốc thời gian quan trọng).
- **Trò chuyện trực tiếp (Side Panel):** Giao diện chat trực quan tích hợp bên lề màn hình làm việc chính để bạn đặt câu hỏi cho AI bất cứ lúc nào.

---

## 🛠 Hướng dẫn cài đặt bằng file đóng gói (.zip)

Để cài đặt tiện ích cho Chrome hoặc Edge từ file đã đóng gói sẵn:

1. Tìm file **[browser-extension.zip](file:///Users/nguyenquocbao/ibib-vic-2026/browser-extension.zip)** ở thư mục gốc của dự án.
2. Giải nén file `.zip` này ra một thư mục trên máy tính của bạn (ví dụ đặt tên thư mục giải nén là `compliance-extension`).
3. Mở trình duyệt và truy cập trang quản lý extension:
   - **Google Chrome:** Gõ `chrome://extensions` vào thanh địa chỉ và nhấn Enter.
   - **Microsoft Edge:** Gõ `edge://extensions` vào thanh địa chỉ và nhấn Enter.
4. Bật chế độ nhà phát triển: gạt công tắc **Developer mode** ở góc trên cùng bên phải sang trạng thái **ON**.
5. Nhấp vào nút **Load unpacked** (Tải thư mục đã giải nén) ở góc trái.
6. Chọn thư mục `out` nằm bên trong thư mục bạn vừa giải nén ở Bước 2.
7. Biểu tượng của tiện ích sẽ hiển thị trên thanh công cụ của trình duyệt.

---

## 📖 Hướng dẫn sử dụng chi tiết

### 1. Đồng bộ đăng nhập
Tiện ích tự động sử dụng chung tài khoản với ứng dụng web chính.
- Mở bảng Side Panel của tiện ích.
- Nếu bạn chưa đăng nhập, click vào nút **Đăng nhập để sử dụng**. Hệ thống sẽ mở trang chủ ứng dụng web chính để bạn đăng nhập.
- Sau khi đăng nhập thành công ở web chính, giao diện tiện ích sẽ tự chuyển sang màn hình chat.

### 2. Sử dụng Side Panel để Chat
- Click vào biểu tượng tiện ích trên thanh công cụ của Chrome/Edge để bật bảng Side Panel bên phải màn hình.
- Nhập câu hỏi nghiệp vụ và nhấn **Enter** hoặc click nút mũi tên để gửi câu hỏi tra cứu tới AI.

### 3. Tóm tắt trang web đang đọc
- Mở một trang báo chí, thông tư hoặc trang tài liệu bất kỳ trên trình duyệt.
- Nhìn vào giao diện Side Panel, bạn sẽ thấy dòng chữ **"Trang đang xem: [Tên trang]"**.
- Click nút **Tóm tắt**. Tiện ích sẽ gửi nội dung trang web sang AI để tóm tắt và hiển thị các điều khoản liên quan.

### 4. Tra cứu nhanh bằng menu chuột phải (Context Menu)
- Khi đọc tài liệu trên trình duyệt, hãy **bôi đen** cụm từ hoặc đoạn văn bản cần tra cứu (ví dụ: *"tỷ lệ an toàn vốn tối thiểu"*).
- Click chuột phải vào phần vừa bôi đen → Chọn **Tra cứu với Sovereign Compliance AI**.
- Giao diện Side Panel sẽ tự động hiển thị và gửi cụm từ bạn vừa chọn để tra cứu trực tiếp.

---

## ⚙️ Cấu hình nâng cao

Bản đóng gói trong file zip đã được cấu hình mặc định chạy với API Cloud: `https://ibib-vic-2026.onrender.com`.

Nếu bạn muốn kết nối với API chạy cục bộ (local) hoặc máy chủ khác:
1. Mở giao diện Side Panel của tiện ích.
2. Click vào biểu tượng **bánh răng cài đặt** (ở góc dưới).
3. Đổi **API URL** thành địa chỉ mới (ví dụ: `http://localhost:8000`).
4. Bạn cũng có thể đổi **Vai trò mặc định** (Nhân viên hoặc Quản lý) để AI đưa ra câu trả lời theo đúng ngữ cảnh mong muốn.
5. Click **Lưu** để áp dụng.
