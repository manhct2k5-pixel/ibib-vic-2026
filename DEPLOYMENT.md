# Hướng dẫn Deployment

## 1. Frontend (React App)

### Build
```bash
cd frontend
npm install
npm run build
```

### Output
- Thư mục: `frontend/dist/`
- File chính: `dist/index.html`
- Assets: `dist/assets/`

### Triển khai

**Vercel (Recommended)**
```bash
npm i -g vercel
vercel --prod
```

**Netlify**
```bash
npm i -g netlify-cli
netlify deploy --prod --dir=dist
```

**GitHub Pages**
1. Thêm vào `package.json`:
```json
"homepage": "https://username.github.io/repo-name"
"scripts": {
  "deploy": "npm run build && gh-pages -d dist"
}
```
2. Cài đặt: `npm i -D gh-pages`
3. Chạy: `npm run deploy`

**Docker**
```dockerfile
FROM nginx:alpine
COPY dist/ /usr/share/nginx/html/
EXPOSE 80
```

### Lưu ý quan trọng
- Frontend kết nối API tại: `http://localhost:8000` (dev) hoặc `VITE_API_BASE_URL` (production)
- Cần cấu hình CORS ở backend nếu deploy khác domain

---

## 2. Browser Extension

### Build
```bash
cd browser-extension
npm install
npm run build
```

### Output
- Thư mục: `browser-extension/out/`
- File cần thiết:
  - `manifest.json`
  - `background.js`
  - `content.js`
  - `content.css`
  - `popup.html`
  - `sidepanel.html`

### Cài đặt Extension (Development)

1. Mở Chrome/Edge
2. Vào `chrome://extensions/` hoặc `edge://extensions/`
3. Bật **Developer mode**
4. Click **Load unpacked**
5. Chọn thư mục `browser-extension/out/`

### Đóng gói Extension

1. Trong `chrome://extensions/`
2. Click **Pack extension**
3. Chọn thư mục `out/`
4. Output: `.crx` và `.pem`

### Chrome Web Store (Production)

1. Tạo tài khoản [Chrome Web Store Developer](https://chrome.google.com/webstore/devconsole)
2. Thanh toán phí đăng ký ($5)
3. Upload file `.zip` chứa:
   - `manifest.json`
   - Tất cả JS/CSS files
   - Icons (128px, 48px, 16px)
4. Điền thông tin:
   - Tên: "Sovereign Compliance AI"
   - Mô tả
   - Screenshots
5. Submit review

### Microsoft Edge Add-ons

1. Đăng ký [Microsoft Edge Add-ons](https://partner.microsoft.com/dashboard/microsoft_edge/)
2. Upload package tương tự Chrome
3. Submit for certification

---

## 3. Backend API (nếu có)

### Yêu cầu
- Python 3.10+
- FastAPI
- Uvicorn

### Cấu hình Environment
```bash
export VITE_API_BASE_URL=https://api.your-domain.com
```

### Deploy Options
- **Railway**: `railway login && railway init`
- **Render**: Connect GitHub repo
- **Fly.io**: `fly launch && fly deploy`
- **AWS ECS**: Container deployment

---

## 4. Cấu hình Production

### Frontend Environment
```bash
# frontend/.env.production
VITE_API_BASE_URL=https://api.your-domain.com
VITE_API_MODE=production
```

### Extension Permissions
Kiểm tra `manifest.json`:
```json
{
  "permissions": [
    "activeTab",
    "contextMenus", 
    "sidePanel",
    "scripting",
    "storage"
  ],
  "host_permissions": ["<all_urls>"]
}
```

---

## 5. Checklist trước Production

- [ ] Frontend build thành công
- [ ] Extension build thành công  
- [ ] API endpoint đúng
- [ ] CORS configured ở backend
- [ ] Extension icons có sẵn (128px, 48px, 16px)
- [ ] Test trên Chrome
- [ ] Test trên Edge
- [ ] Privacy policy và Terms of Service sẵn sàng

---

## 6. Testing

### Frontend
```bash
cd frontend
npm run preview
# Mở http://localhost:4173
```

### Extension
1. Load unpacked từ `out/`
2. Test popup click
3. Test side panel
4. Test content script (bôi đen text → click extension)

---

## Liên hệ hỗ trợ
- Issues: https://github.com/your-org/ibib-vic-2026/issues
